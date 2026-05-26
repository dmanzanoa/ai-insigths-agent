from __future__ import annotations

import json
from concurrent.futures import ThreadPoolExecutor, as_completed
from typing import Any

import pandas as pd

from .aggregates import build_project_aggregates
from .aws_clients import AwsClients
from .bedrock_client import generate_insights
from .compression import compress_with_cache
from .config import DATA_SOURCES, Settings, settings
from .historical import build_weekly_comparison, load_previous_snapshot
from .insights_dataframe import build_insights_dataframe
from .loaders import load_parquet_folder
from .outputs import save_all_outputs, save_structured_dataframe_to_s3
from .preprocessing import build_conversations, clean_raw_dataframe
from .prompts import insight_template_for_label, render_prompt
from .schemas import default_summary
from .state import AgentState
from .text_features import build_lenguaje_cliente_global


def action_load_and_assess(clients: AwsClients, state: AgentState, cfg: Settings = settings) -> AgentState:
    print(f"\n[AGENT] Loading data for {state.label}")
    df = load_parquet_folder(clients, DATA_SOURCES[state.label], cfg)
    if df.empty:
        state.add_error("No data found", terminal=True)
        return state

    try:
        df = clean_raw_dataframe(df)
    except Exception as exc:
        state.add_error(f"Input validation failed: {exc}", terminal=True)
        return state

    state.df = df
    state.quality_metrics = {
        "total_rows": float(len(df)),
        "unique_clients": float(df["clientId"].nunique()),
        "null_pct": float(df.isnull().sum().sum() / max(len(df) * len(df.columns), 1)),
        "avg_text_length": float(df["text"].astype(str).str.len().mean()),
    }
    state.decisions_made.append(f"Loaded {len(df)} rows, {int(state.quality_metrics['unique_clients'])} clients")
    print(f"Quality metrics: {state.quality_metrics}")
    return state


def action_preprocess(_: AwsClients, state: AgentState, cfg: Settings = settings) -> AgentState:
    print("\n[AGENT] Preprocessing conversations")
    if state.df is None:
        state.add_error("Cannot preprocess without raw dataframe", terminal=True)
        return state
    state.conversaciones = build_conversations(state.df)
    state.decisions_made.append(f"Preprocessed {len(state.conversaciones)} conversations")
    return state


def action_compress(clients: AwsClients, state: AgentState, cfg: Settings = settings) -> AgentState:
    print("\n[AGENT] Compressing conversations")
    if state.conversaciones is None:
        state.add_error("Cannot compress without conversations", terminal=True)
        return state

    strategy = state.compression_strategy or {"max_retries": cfg.max_compress_retries, "temperature": 0.0}
    max_retries = int(strategy.get("max_retries", cfg.max_compress_retries))
    temperature = float(strategy.get("temperature", 0.0))
    summaries: list[tuple[int, dict[str, Any]]] = []

    with ThreadPoolExecutor(max_workers=cfg.default_compress_workers) as executor:
        futures = {
            executor.submit(
                compress_with_cache,
                clients,
                state.label,
                row["clientId"],
                row["conversacion"],
                max_retries=max_retries,
                temperature=temperature,
                cfg=cfg,
            ): idx
            for idx, row in state.conversaciones.iterrows()
        }

        for future in as_completed(futures):
            idx = futures[future]
            try:
                summary = future.result()
            except Exception as exc:
                state.errors.append(f"Compression failed for row {idx}: {exc}")
                summary = default_summary()
            summaries.append((idx, summary))

    summaries.sort(key=lambda item: item[0])
    conversaciones = state.conversaciones.copy()
    conversaciones["summary"] = [summary for _, summary in summaries]
    state.conversaciones = conversaciones
    state.compress_done = True
    state.decisions_made.append(f"Compressed {len(summaries)} conversations")
    return state


def action_build_insights_df(clients: AwsClients, state: AgentState, cfg: Settings = settings) -> AgentState:
    print("\n[AGENT] Building insights dataframe")
    if state.conversaciones is None or state.df is None:
        state.add_error("Cannot build insights dataframe without source data", terminal=True)
        return state
    insights_df = build_insights_dataframe(state.conversaciones, state.df, state.label)
    state.insights_df = insights_df
    save_structured_dataframe_to_s3(clients, insights_df, state.label, cfg)
    state.decisions_made.append(f"Built insights dataframe with {len(insights_df)} rows")
    return state


def action_build_aggregates(_: AwsClients, state: AgentState, cfg: Settings = settings) -> AgentState:
    print("\n[AGENT] Building aggregates")
    if state.insights_df is None or state.conversaciones is None:
        state.add_error("Cannot build aggregates without insights data", terminal=True)
        return state
    aggregates = build_project_aggregates(state.insights_df)
    aggregates["lenguaje_cliente"] = build_lenguaje_cliente_global(state.conversaciones)
    state.aggregates = aggregates
    state.decisions_made.append("Built detailed aggregates")
    return state


def action_load_historical_context(clients: AwsClients, state: AgentState, cfg: Settings = settings) -> AgentState:
    print("\n[AGENT] Loading historical context")
    state.historical_context = load_previous_snapshot(clients, state.label, cfg)
    state.decisions_made.append("Loaded historical context")
    return state


def action_build_weekly_comparison(_: AwsClients, state: AgentState, cfg: Settings = settings) -> AgentState:
    print("\n[AGENT] Building weekly comparison")
    state.weekly_comparison = build_weekly_comparison(
        state.label,
        state.aggregates or {},
        state.historical_context,
    )
    state.decisions_made.append("Built weekly comparison from snapshots")
    return state


def action_generate_general_insights(clients: AwsClients, state: AgentState, cfg: Settings = settings) -> AgentState:
    print("\n[AGENT] Generating general insights")
    if state.aggregates is None:
        state.add_error("Cannot generate general insights without aggregates", terminal=True)
        return state

    structured_input = json.dumps(state.aggregates, ensure_ascii=False, indent=2)
    final_prompt = render_prompt(
        insight_template_for_label(state.label),
        datos_estructurados=structured_input,
        contexto_historico=json.dumps(state.weekly_comparison, ensure_ascii=False, indent=2),
    )

    try:
        state.general_insights = generate_insights(clients, final_prompt, cfg=cfg)
        state.decisions_made.append("Generated general insights")
    except Exception as exc:
        state.add_error(f"General insights generation failed: {exc}", terminal=True)
    return state


def action_validate_general_insights(_: AwsClients, state: AgentState, cfg: Settings = settings) -> AgentState:
    print("\n[AGENT] Validating general insights")
    state.validation_attempts += 1
    try:
        json.loads(state.general_insights or "")
        state.decisions_made.append("Validated general insights")
    except Exception as exc:
        state.add_error(f"Validation failed: {exc}", terminal=True)
    return state


def _add_language(aggregated: dict, df_slice: pd.DataFrame, conversaciones: pd.DataFrame) -> dict:
    client_ids = set(df_slice["clientId"])
    conv_slice = conversaciones[conversaciones["clientId"].isin(client_ids)]
    aggregated["lenguaje_cliente"] = build_lenguaje_cliente_global(conv_slice)
    return aggregated


def action_generate_tendencias(clients: AwsClients, state: AgentState, cfg: Settings = settings) -> AgentState:
    print("\n[AGENT] Generating tendencias")
    if state.insights_df is None or state.conversaciones is None:
        state.add_error("Cannot generate tendencias without insights data", terminal=True)
        return state

    insights_df = state.insights_df.copy()
    insights_df["createdAt"] = pd.to_datetime(insights_df["createdAt"], errors="coerce")
    insights_df = insights_df[insights_df["createdAt"].notna()].copy()
    insights_df["mes"] = insights_df["createdAt"].dt.to_period("M").astype(str)

    for mes, df_mes in insights_df.groupby("mes"):
        aggregated = _add_language(build_project_aggregates(df_mes), df_mes, state.conversaciones)
        final_prompt = render_prompt(
            "tendencias_lidz.j2",
            mes=mes,
            datos_estructurados=json.dumps(aggregated, ensure_ascii=False, indent=2),
        )
        try:
            state.tendencias_insights[mes] = generate_insights(clients, final_prompt, cfg=cfg)
        except Exception as exc:
            state.errors.append(f"Tendencias for {mes} failed: {exc}")

    state.tendencias_done = True
    state.decisions_made.append(f"Generated {len(state.tendencias_insights)} monthly tendencias")
    return state


def _generate_segment_insights(
    clients: AwsClients,
    state: AgentState,
    column: str,
    context_label: str,
    cfg: Settings,
) -> dict[str, str]:
    assert state.insights_df is not None
    assert state.conversaciones is not None

    insights_df = state.insights_df[state.insights_df[column].notna()].copy()
    values = insights_df[column].astype(str).unique().tolist()
    template_name = insight_template_for_label(state.label)
    results: dict[str, str] = {}
    failures: dict[str, str] = {}
    parallel_key = "parallelize_subprojects" if column == "subProjectInfo" else "parallelize_marcas"
    should_parallelize = state.parallelization_strategy.get(parallel_key, False)
    max_workers = int(state.parallelization_strategy.get("max_workers", 1))

    def build_prompt(value: str) -> str:
        df_slice = insights_df[insights_df[column].astype(str) == value]
        aggregated = _add_language(build_project_aggregates(df_slice), df_slice, state.conversaciones)
        return render_prompt(
            template_name,
            contexto=f"{context_label}: {value}",
            datos_estructurados=json.dumps(aggregated, ensure_ascii=False, indent=2),
        )

    if should_parallelize and len(values) > 1:
        with ThreadPoolExecutor(max_workers=max_workers) as executor:
            futures = {}
            for value in values:
                prompt = build_prompt(value)
                futures[value] = (executor.submit(generate_insights, clients, prompt, max_retries=3, cfg=cfg), prompt)
            for value, (future, prompt) in futures.items():
                try:
                    results[value] = future.result()
                except Exception:
                    failures[value] = prompt
    else:
        for value in values:
            prompt = build_prompt(value)
            try:
                results[value] = generate_insights(clients, prompt, max_retries=3, cfg=cfg)
            except Exception:
                failures[value] = prompt

    for value, prompt in failures.items():
        try:
            results[value] = generate_insights(clients, prompt, max_retries=5, cfg=cfg)
        except Exception as exc:
            state.errors.append(f"{context_label} {value} failed after retries: {exc}")

    return results


def action_generate_subproject_insights(clients: AwsClients, state: AgentState, cfg: Settings = settings) -> AgentState:
    print("\n[AGENT] Generating subproject insights")
    if state.insights_df is None or "subProjectInfo" not in state.insights_df.columns:
        state.subprojects_done = True
        return state
    state.subproject_insights = _generate_segment_insights(clients, state, "subProjectInfo", "Proyecto", cfg)
    state.subprojects_done = True
    state.decisions_made.append(f"Generated {len(state.subproject_insights)} subproject insights")
    return state


def action_generate_marca_insights(clients: AwsClients, state: AgentState, cfg: Settings = settings) -> AgentState:
    print("\n[AGENT] Generating marca insights")
    if state.insights_df is None or "Marca" not in state.insights_df.columns:
        state.marcas_done = True
        return state
    state.marca_insights = _generate_segment_insights(clients, state, "Marca", "Marca", cfg)
    state.marcas_done = True
    state.decisions_made.append(f"Generated {len(state.marca_insights)} marca insights")
    return state


def action_save_all_outputs(clients: AwsClients, state: AgentState, cfg: Settings = settings) -> AgentState:
    print("\n[AGENT] Saving outputs")
    if not state.terminal_error:
        save_all_outputs(clients, state, cfg)
        state.decisions_made.append("Saved all outputs")
    else:
        print("Skipping output save because the pipeline ended with a terminal error")
    return state


ACTION_MAP = {
    "load": action_load_and_assess,
    "preprocess": action_preprocess,
    "compress": action_compress,
    "build_insights_df": action_build_insights_df,
    "build_aggregates": action_build_aggregates,
    "load_historical_context": action_load_historical_context,
    "build_weekly_comparison": action_build_weekly_comparison,
    "generate_general": action_generate_general_insights,
    "validate_general": action_validate_general_insights,
    "generate_tendencias": action_generate_tendencias,
    "generate_subproject": action_generate_subproject_insights,
    "generate_marca": action_generate_marca_insights,
    "save_all": action_save_all_outputs,
}

