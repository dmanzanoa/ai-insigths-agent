from __future__ import annotations

import datetime as dt
import hashlib
import json
import re
import threading
from typing import Any

from botocore.exceptions import ClientError

from .aws_clients import AwsClients
from .bedrock_client import invoke_text
from .config import Settings, settings
from .prompts import render_prompt
from .schemas import COMPRESS_SCHEMA_SPEC, default_summary


CACHE_STATS = {"hit": 0, "miss": 0, "error": 0}
CACHE_STATS_LOCK = threading.Lock()


def build_conversation_hash(label: str, client_id: str, conversation_text: str, cfg: Settings = settings) -> str:
    raw = f"{cfg.summary_version}||{label}||{client_id}||{conversation_text}".encode("utf-8")
    return hashlib.sha256(raw).hexdigest()


def compress(
    clients: AwsClients,
    text: str,
    *,
    temperature: float = 0.0,
    cfg: Settings = settings,
) -> str:
    prompt = render_prompt(
        "compress.j2",
        schema=COMPRESS_SCHEMA_SPEC,
        conversation_text=text,
    )
    return invoke_text(
        clients,
        cfg.model_compress,
        prompt,
        max_tokens=250,
        temperature=temperature,
    )


def parse_compress_output(text: str) -> dict[str, str]:
    parsed = default_summary()
    lines = re.split(r"[,\n]", text)
    for line in lines:
        line = line.strip()
        if not line:
            continue
        match = re.match(r"([^:=]+)\s*[:=]\s*(.+)", line)
        if not match:
            continue
        key, value = match.groups()
        key = key.strip()
        value = value.strip().lower()
        if key in parsed:
            parsed[key] = value
    return parsed


def validate_compress_schema(parsed: dict[str, Any]) -> tuple[bool, dict[str, str]]:
    errors: dict[str, str] = {}
    for field, allowed in COMPRESS_SCHEMA_SPEC.items():
        value = parsed.get(field)
        if value is None or value == "":
            errors[field] = "missing"
            continue
        normalized = str(value).lower().strip()
        if allowed and normalized not in allowed and normalized != "desconocido":
            errors[field] = f"invalid: {value}"
    return len(errors) == 0, errors


def compress_with_validation(
    clients: AwsClients,
    text: str,
    *,
    max_retries: int | None = None,
    temperature: float = 0.0,
    cfg: Settings = settings,
) -> dict[str, str]:
    attempts = max_retries or cfg.max_compress_retries
    for _ in range(1, attempts + 1):
        output = compress(clients, text, temperature=temperature, cfg=cfg)
        parsed = parse_compress_output(output)
        is_valid, _ = validate_compress_schema(parsed)
        if is_valid:
            return parsed
    print("Compression failed after retries")
    return default_summary()


def compress_with_cache(
    clients: AwsClients,
    label: str,
    client_id: str,
    conversation_text: str,
    *,
    max_retries: int | None = None,
    temperature: float = 0.0,
    cfg: Settings = settings,
) -> dict[str, Any]:
    conversation_hash = build_conversation_hash(label, client_id, conversation_text, cfg)
    key = f"{cfg.summary_cache_prefix}/{label}/{conversation_hash}.json"

    try:
        resp = clients.s3.get_object(Bucket=cfg.output_bucket, Key=key)
        payload = json.loads(resp["Body"].read().decode("utf-8"))
        if payload.get("summary_version") == cfg.summary_version:
            with CACHE_STATS_LOCK:
                CACHE_STATS["hit"] += 1
            return payload.get("summary") or default_summary()
    except ClientError:
        pass
    except Exception:
        with CACHE_STATS_LOCK:
            CACHE_STATS["error"] += 1

    with CACHE_STATS_LOCK:
        CACHE_STATS["miss"] += 1

    summary = compress_with_validation(
        clients,
        conversation_text,
        max_retries=max_retries,
        temperature=temperature,
        cfg=cfg,
    )
    payload = {
        "label": label,
        "clientId": str(client_id),
        "conversation_hash": conversation_hash,
        "summary_version": cfg.summary_version,
        "summary": summary,
        "cached_at": dt.datetime.utcnow().isoformat() + "Z",
    }
    clients.s3.put_object(
        Bucket=cfg.output_bucket,
        Key=key,
        Body=json.dumps(payload, ensure_ascii=False).encode("utf-8"),
        ContentType="application/json",
    )
    return summary

