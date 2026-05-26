from __future__ import annotations

import json

from .aws_clients import AwsClients
from .config import Settings, settings
from .json_utils import extract_json_object


def invoke_text(
    clients: AwsClients,
    model_id: str,
    prompt: str,
    *,
    max_tokens: int,
    temperature: float,
) -> str:
    payload = {
        "anthropic_version": "bedrock-2023-05-31",
        "messages": [{"role": "user", "content": prompt}],
        "max_tokens": max_tokens,
        "temperature": temperature,
    }
    resp = clients.bedrock.invoke_model(modelId=model_id, body=json.dumps(payload).encode("utf-8"))
    data = json.loads(resp["body"].read().decode("utf-8"))
    return data["content"][0]["text"]


def generate_insights(
    clients: AwsClients,
    prompt: str,
    *,
    max_retries: int = 3,
    cfg: Settings = settings,
) -> str:
    last_error: Exception | None = None
    for attempt in range(1, max_retries + 1):
        try:
            text = invoke_text(
                clients,
                cfg.model_main,
                prompt,
                max_tokens=8000,
                temperature=0.3,
            )
            obj = extract_json_object(text)
            return json.dumps(obj, ensure_ascii=False, indent=2)
        except Exception as exc:
            last_error = exc
            if attempt < max_retries:
                print(f"Warning: Bedrock insight attempt {attempt}/{max_retries} failed; retrying...")
    raise ValueError(f"Failed to generate valid JSON after {max_retries} attempts: {last_error}") from last_error

