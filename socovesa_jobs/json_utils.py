from __future__ import annotations

import json
import re
from typing import Any


def strip_markdown_json(text: str) -> str:
    text = re.sub(r"```\s*json\s*", "", text)
    text = re.sub(r"```\s*", "", text)
    return text.strip()


def extract_json_object(text: str) -> dict[str, Any]:
    clean_text = strip_markdown_json(text)
    start_idx = clean_text.find("{")
    if start_idx == -1:
        raise ValueError(f"No JSON object found in response: {clean_text[:200]}")

    decoder = json.JSONDecoder()
    obj, _ = decoder.raw_decode(clean_text[start_idx:])
    if not isinstance(obj, dict):
        raise ValueError(f"Expected JSON object, got {type(obj).__name__}")
    return obj


def validate_json_output(json_text: str) -> dict[str, Any]:
    try:
        parsed = json.loads(json_text)
    except json.JSONDecodeError as exc:
        raise ValueError(f"Output is not valid JSON: {exc}") from exc

    if not isinstance(parsed, dict):
        raise ValueError("Output root must be a JSON object")
    return parsed

