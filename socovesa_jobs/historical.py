from __future__ import annotations

import datetime as dt
import json
from typing import Any

from botocore.exceptions import ClientError

from .aws_clients import AwsClients
from .config import Settings, settings


def current_week_id(now: dt.date | None = None) -> str:
    today = now or dt.datetime.utcnow().date()
    iso = today.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def previous_week_id(now: dt.date | None = None) -> str:
    today = now or dt.datetime.utcnow().date()
    previous = today - dt.timedelta(days=7)
    iso = previous.isocalendar()
    return f"{iso.year}-W{iso.week:02d}"


def snapshot_key(label: str, week_id: str, cfg: Settings = settings) -> str:
    return f"{cfg.snapshot_prefix}/{label}/week={week_id}/snapshot.json"


def load_previous_snapshot(clients: AwsClients, label: str, cfg: Settings = settings) -> dict[str, Any]:
    prev_week = previous_week_id()
    key = snapshot_key(label, prev_week, cfg)
    try:
        resp = clients.s3.get_object(Bucket=cfg.output_bucket, Key=key)
        previous_snapshot = json.loads(resp["Body"].read().decode("utf-8"))
        print(f"Previous snapshot loaded: {prev_week}")
        return {
            "source": "s3_weekly_snapshot",
            "previous_week": prev_week,
            "previous_snapshot": previous_snapshot,
        }
    except ClientError:
        print(f"No previous snapshot found for {prev_week}")
        return {
            "source": "none",
            "previous_week": prev_week,
            "previous_snapshot": None,
        }


def build_weekly_comparison(label: str, aggregates: dict[str, Any], historical_context: dict[str, Any]) -> dict[str, Any]:
    current_week = current_week_id()
    previous_snapshot = historical_context.get("previous_snapshot")
    current_snapshot = {
        "label": label,
        "week": current_week,
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "aggregates": aggregates,
    }
    return {
        "current_week": current_week,
        "previous_week": historical_context.get("previous_week"),
        "previous_snapshot_available": previous_snapshot is not None,
        "previous_snapshot": previous_snapshot,
        "current_snapshot": current_snapshot,
        "instruction": (
            "Compara la semana actual contra la semana anterior usando snapshots estructurados. "
            "No compares contra insights narrativos anteriores. "
            "No inventes metricas. Usa solo current_snapshot y previous_snapshot."
        ),
    }


def save_current_week_snapshot(clients: AwsClients, label: str, aggregates: dict[str, Any], cfg: Settings = settings) -> None:
    week = current_week_id()
    key = snapshot_key(label, week, cfg)
    snapshot = {
        "label": label,
        "week": week,
        "generated_at": dt.datetime.utcnow().isoformat() + "Z",
        "aggregates": aggregates,
    }
    clients.s3.put_object(
        Bucket=cfg.output_bucket,
        Key=key,
        Body=json.dumps(snapshot, ensure_ascii=False, indent=2).encode("utf-8"),
        ContentType="application/json",
    )
    print(f"Saved weekly snapshot: s3://{cfg.output_bucket}/{key}")

