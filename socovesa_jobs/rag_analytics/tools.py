from __future__ import annotations

import json
from typing import Any

from .snapshot_store import load_snapshots_from_chunks
from ..aws_clients import AwsClients


def _metric_rows(aggregates: dict[str, Any], metric: str) -> Any:
    return (
        aggregates.get(metric)
        or aggregates.get("funnel", {}).get(metric)
        or aggregates.get("conversion", {}).get(metric)
        or aggregates.get("financiamiento", {}).get(metric)
        or []
    )


def get_category_distribution(clients: AwsClients, metric: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    snapshots = load_snapshots_from_chunks(clients, chunks)
    rows = []

    for snapshot in snapshots:
        metric_rows = _metric_rows(snapshot.get("aggregates", {}), metric)
        if not isinstance(metric_rows, list):
            continue

        for row in metric_rows:
            if not isinstance(row, dict):
                continue
            categoria = row.get("categoria")
            porcentaje = row.get("porcentaje")
            conteo = row.get("conteo")
            if categoria is None or porcentaje is None:
                continue
            rows.append(
                {
                    "categoria": str(categoria),
                    "porcentaje": round(float(porcentaje) * 100, 2),
                    "conteo": int(conteo) if conteo is not None else None,
                }
            )

    deduped = {row["categoria"]: row for row in rows}
    data = list(deduped.values())
    return {
        "type": "bar_chart" if data else "none",
        "title": f"Distribucion de {metric}",
        "xKey": "categoria",
        "yKey": "porcentaje",
        "data": data,
    }


def get_weekly_metric_trend(clients: AwsClients, metric: str, chunks: list[dict[str, Any]]) -> dict[str, Any]:
    snapshots = load_snapshots_from_chunks(clients, chunks)
    data = []

    for snapshot in snapshots:
        week = snapshot.get("week")
        metric_rows = _metric_rows(snapshot.get("aggregates", {}), metric)
        if not week or not isinstance(metric_rows, list):
            continue

        row_data = {"week": week}
        for row in metric_rows:
            if not isinstance(row, dict):
                continue
            categoria = row.get("categoria")
            porcentaje = row.get("porcentaje")
            if categoria is not None and porcentaje is not None:
                row_data[str(categoria)] = round(float(porcentaje) * 100, 2)

        if len(row_data) > 1:
            data.append(row_data)

    data = sorted(data, key=lambda item: item.get("week", ""))
    y_keys = sorted({key for row in data for key in row if key != "week"})
    return {
        "type": "line_chart" if data and y_keys else "none",
        "title": f"Evolucion semanal de {metric}",
        "xKey": "week",
        "yKeys": y_keys,
        "data": data,
    }


def execute_tool(clients: AwsClients, tool_decision: dict[str, Any], chunks: list[dict[str, Any]]) -> dict[str, Any]:
    tool = tool_decision.get("tool")
    metric = tool_decision.get("metric", "general")

    if tool == "get_category_distribution":
        return get_category_distribution(clients, str(metric), chunks)
    if tool == "get_weekly_metric_trend":
        return get_weekly_metric_trend(clients, str(metric), chunks)

    return {"type": "none", "data": []}

