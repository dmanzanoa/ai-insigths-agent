from __future__ import annotations

import json
from typing import Any

from socovesa_jobs.aws_clients import create_aws_clients
from socovesa_jobs.config import settings
from socovesa_jobs.rag_analytics.service import AnalyticsRagService


clients = create_aws_clients(settings)
service = AnalyticsRagService(clients, settings)


def cors_response(status_code: int, body: dict[str, Any] | str = "") -> dict[str, Any]:
    return {
        "statusCode": status_code,
        "headers": {
            "Access-Control-Allow-Origin": "*",
            "Access-Control-Allow-Headers": "Content-Type,Authorization",
            "Access-Control-Allow-Methods": "POST,OPTIONS",
            "Content-Type": "application/json",
        },
        "body": json.dumps(body, ensure_ascii=False) if isinstance(body, dict) else body,
    }


def lambda_handler(event: dict[str, Any], context: Any) -> dict[str, Any]:
    method = event.get("requestContext", {}).get("http", {}).get("method")
    if method == "OPTIONS":
        return cors_response(200, "")

    try:
        body = json.loads(event.get("body") or "{}")
        return cors_response(200, service.answer(body))
    except ValueError as exc:
        return cors_response(400, {"error": str(exc)})
    except Exception as exc:
        return cors_response(500, {"error": str(exc)})

