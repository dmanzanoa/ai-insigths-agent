from __future__ import annotations

import json
from typing import Any

from .types import Chunk
from ..aws_clients import AwsClients


def load_snapshot_from_chunk(clients: AwsClients, chunk: Chunk) -> dict[str, Any] | None:
    try:
        uri = chunk.get("location", {}).get("s3Location", {}).get("uri")
        if not uri:
            return None

        bucket_key = uri.replace("s3://", "")
        bucket, key = bucket_key.split("/", 1)
        response = clients.s3.get_object(Bucket=bucket, Key=key)
        return json.loads(response["Body"].read().decode("utf-8"))
    except Exception as exc:
        print("SNAPSHOT_LOAD_ERROR:", str(exc))
        return None


def load_snapshots_from_chunks(clients: AwsClients, chunks: list[Chunk]) -> list[dict[str, Any]]:
    snapshots = []
    seen = set()

    for chunk in chunks:
        uri = chunk.get("location", {}).get("s3Location", {}).get("uri")
        if not uri or uri in seen:
            continue
        seen.add(uri)
        snapshot = load_snapshot_from_chunk(clients, chunk)
        if snapshot:
            snapshots.append(snapshot)

    return snapshots

