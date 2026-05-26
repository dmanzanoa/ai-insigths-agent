from __future__ import annotations

import io

import pandas as pd
import pyarrow.parquet as pq

from .aws_clients import AwsClients
from .config import Settings, settings


def load_parquet_folder(clients: AwsClients, prefix: str, cfg: Settings = settings) -> pd.DataFrame:
    dfs: list[pd.DataFrame] = []
    continuation_token: str | None = None

    while True:
        kwargs = {"Bucket": cfg.s3_bucket, "Prefix": prefix}
        if continuation_token:
            kwargs["ContinuationToken"] = continuation_token
        resp = clients.s3.list_objects_v2(**kwargs)

        for obj in resp.get("Contents", []):
            if obj["Key"].endswith(".parquet"):
                raw = clients.s3.get_object(Bucket=cfg.s3_bucket, Key=obj["Key"])
                table = pq.read_table(io.BytesIO(raw["Body"].read()))
                dfs.append(table.to_pandas())

        if not resp.get("IsTruncated"):
            break
        continuation_token = resp.get("NextContinuationToken")

    return pd.concat(dfs, ignore_index=True) if dfs else pd.DataFrame()

