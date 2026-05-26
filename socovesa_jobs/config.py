from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any


BASE_DIR = Path(__file__).resolve().parents[1]
PROMPTS_DIR = BASE_DIR / "prompts"


DATA_SOURCES: dict[str, str] = {
    "subsidio": os.getenv("DATA_SOURCE_SUBSIDIO", "data/subsidio/"),
    "no_subsidio": os.getenv("DATA_SOURCE_NO_SUBSIDIO", "data/no_subsidio/"),
    "recomendador": os.getenv("DATA_SOURCE_RECOMENDADOR", "data/recomendador/"),
}


@dataclass(frozen=True)
class Settings:
    aws_region: str = os.getenv("AWS_REGION", "us-east-2")
    s3_bucket: str = os.getenv("S3_BUCKET", "")
    output_bucket: str = os.getenv("OUTPUT_BUCKET", "")
    model_main: str = os.getenv(
        "MODEL_MAIN",
        os.getenv("MODEL_ID", "global.anthropic.claude-sonnet-4-5-20250929-v1:0"),
    )
    model_compress: str = os.getenv(
        "MODEL_COMPRESS",
        "global.anthropic.claude-haiku-4-5-20251001-v1:0",
    )
    bedrock_kb_id: str = os.getenv("BEDROCK_KB_ID", "")
    bedrock_kb_data_source_id: str = os.getenv("BEDROCK_KB_DATA_SOURCE_ID", "")
    analytics_kb_id: str = os.getenv("KB_ID", os.getenv("BEDROCK_KB_ID", ""))
    pdf_bucket: str = os.getenv("PDF_BUCKET", os.getenv("OUTPUT_BUCKET", ""))
    pdf_prefix: str = os.getenv("PDF_PREFIX", "insights/temp_pdf_reports")
    pdf_expires_seconds: int = int(os.getenv("PDF_EXPIRES_SECONDS", "3600"))
    structured_data_prefix: str = os.getenv("STRUCTURED_DATA_PREFIX", "insights/structured_data")
    snapshot_prefix: str = os.getenv("SNAPSHOT_PREFIX", "insights/snapshots")
    comparative_insights_prefix: str = os.getenv("COMPARATIVE_INSIGHTS_PREFIX", "insights/comparative")
    insights_prefix: str = os.getenv("INSIGHTS_PREFIX", "insights/generated")
    summary_cache_prefix: str = os.getenv("SUMMARY_CACHE_PREFIX", "insights/cache/conversation_summaries")
    summary_version: str = "v8"
    max_compress_retries: int = 3
    default_compress_workers: int = int(os.getenv("COMPRESS_WORKERS", "2"))


def boto_config() -> Any:
    from botocore.config import Config

    return Config(
        read_timeout=1000,
        retries={"max_attempts": 3, "mode": "standard"},
        max_pool_connections=10,
    )


settings = Settings()
