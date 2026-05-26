from __future__ import annotations

import datetime as dt
import io
import re

import pandas as pd

from .aws_clients import AwsClients
from .config import Settings, settings
from .historical import current_week_id, save_current_week_snapshot
from .state import AgentState


def slugify(value: str) -> str:
    value = re.sub(r"[^a-zA-Z0-9_-]+", "_", str(value).strip().lower())
    return re.sub(r"_+", "_", value).strip("_") or "unknown"


def save_structured_dataframe_to_s3(
    clients: AwsClients,
    df: pd.DataFrame,
    label: str,
    cfg: Settings = settings,
) -> None:
    if df.empty:
        print("No structured data to save")
        return

    now = dt.datetime.utcnow().strftime("%Y%m%d_%H%M%S")
    key = f"{cfg.structured_data_prefix}/{label}/insights_dataframe_{now}.csv"
    df_to_save = df.copy()
    for col_name in df_to_save.columns:
        if pd.api.types.is_datetime64_any_dtype(df_to_save[col_name]):
            df_to_save[col_name] = df_to_save[col_name].astype(str)

    buffer = io.StringIO()
    df_to_save.to_csv(buffer, index=False, encoding="utf-8")
    clients.s3.put_object(
        Bucket=cfg.output_bucket,
        Key=key,
        Body=buffer.getvalue().encode("utf-8"),
        ContentType="text/csv",
    )
    print(f"Structured dataframe saved: s3://{cfg.output_bucket}/{key}")


def sync_bedrock_knowledge_base(clients: AwsClients, cfg: Settings = settings) -> None:
    if not cfg.bedrock_kb_id or not cfg.bedrock_kb_data_source_id:
        print("Bedrock KB sync skipped: missing BEDROCK_KB_ID or BEDROCK_KB_DATA_SOURCE_ID")
        return
    try:
        clients.bedrock_agent.start_ingestion_job(
            knowledgeBaseId=cfg.bedrock_kb_id,
            dataSourceId=cfg.bedrock_kb_data_source_id,
        )
        print("Bedrock Knowledge Base ingestion started")
    except Exception as exc:
        print(f"Bedrock KB ingestion failed: {exc}")


def save_all_outputs(clients: AwsClients, state: AgentState, cfg: Settings = settings) -> None:
    label = state.label
    if state.aggregates is not None:
        save_current_week_snapshot(clients, label, state.aggregates, cfg)

    if state.general_insights:
        week = current_week_id()
        latest_key = f"{cfg.insights_prefix}/{label}/insights.json"
        weekly_key = f"{cfg.comparative_insights_prefix}/{label}/week={week}/insights.json"
        for key in [latest_key, weekly_key]:
            clients.s3.put_object(
                Bucket=cfg.output_bucket,
                Key=key,
                Body=state.general_insights.encode("utf-8"),
                ContentType="application/json",
            )
        print("Saved latest and weekly comparative insights")

    for mes, json_text in state.tendencias_insights.items():
        key = f"{cfg.insights_prefix}_tendencias/{label}/insights_tendencias_{mes}.json"
        clients.s3.put_object(Bucket=cfg.output_bucket, Key=key, Body=json_text.encode("utf-8"), ContentType="application/json")

    for project, json_text in state.subproject_insights.items():
        key = f"{cfg.insights_prefix}_by_project/{label}/{slugify(project)}/insights.json"
        clients.s3.put_object(Bucket=cfg.output_bucket, Key=key, Body=json_text.encode("utf-8"), ContentType="application/json")

    for marca, json_text in state.marca_insights.items():
        key = f"{cfg.insights_prefix}_by_marca/{label}/{slugify(marca)}/insights.json"
        clients.s3.put_object(Bucket=cfg.output_bucket, Key=key, Body=json_text.encode("utf-8"), ContentType="application/json")

    print(
        "Saved outputs: "
        f"{len(state.tendencias_insights)} tendencias, "
        f"{len(state.subproject_insights)} subprojects, "
        f"{len(state.marca_insights)} marcas"
    )
    sync_bedrock_knowledge_base(clients, cfg)
