from __future__ import annotations

import pandas as pd


REQUIRED_COLUMNS = {"clientId", "createdAt", "sender", "text", "subProjectInfo"}


def validate_input_schema(df: pd.DataFrame) -> None:
    missing = REQUIRED_COLUMNS - set(df.columns)
    if missing:
        raise ValueError(f"Input data missing required columns: {sorted(missing)}")


def clean_raw_dataframe(df: pd.DataFrame) -> pd.DataFrame:
    validate_input_schema(df)
    df = df.copy()
    df["createdAt"] = pd.to_datetime(df["createdAt"], errors="coerce")
    df["text"] = df["text"].astype(str).str.strip()
    df = df[df["text"].str.len() > 1]
    return df.sort_values(["clientId", "createdAt"])


def merge_full_conversation(group: pd.DataFrame) -> str:
    messages: list[str] = []
    for _, row in group.iterrows():
        sender = str(row["sender"]).upper()
        text = str(row["text"]).strip()
        if text:
            messages.append(f"{sender}: {text}")
    return "\n".join(messages)


def build_conversations(df: pd.DataFrame) -> pd.DataFrame:
    conversaciones = (
        df.groupby("clientId")
        .apply(merge_full_conversation)
        .reset_index(name="conversacion")
    )

    meta_cols = ["subProjectInfo"]
    if "Marca" in df.columns:
        meta_cols.append("Marca")
    meta = df.groupby("clientId").agg({col: "first" for col in meta_cols}).reset_index()
    return conversaciones.merge(meta, on="clientId", how="left")

