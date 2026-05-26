from __future__ import annotations

import pandas as pd

from .schemas import INSIGHT_COLUMNS


def _record_from_summary(row: pd.Series) -> dict:
    parsed = row["summary"] or {}
    record = {
        "clientId": row.get("clientId"),
        "createdAt": row.get("createdAt"),
        "subProjectInfo": row.get("subProjectInfo"),
        "Marca": row.get("Marca"),
    }
    for out_col, summary_key in INSIGHT_COLUMNS.items():
        if out_col in record:
            continue
        record[out_col] = parsed.get(summary_key, "desconocido")
    return record


def build_insights_dataframe(conversaciones: pd.DataFrame, df_raw: pd.DataFrame, label: str) -> pd.DataFrame:
    df_raw = df_raw.copy()
    df_raw["createdAt"] = pd.to_datetime(df_raw["createdAt"], errors="coerce")
    has_marca = "Marca" in df_raw.columns

    if label in ("subsidio", "no_subsidio"):
        agg_dict = {"createdAt": ("createdAt", "min"), "subProjectInfo": ("subProjectInfo", "first")}
        if has_marca:
            agg_dict["Marca"] = ("Marca", "first")
        meta = df_raw.sort_values("createdAt").groupby("clientId").agg(**agg_dict).reset_index()
        drop_cols = [col for col in ["subProjectInfo", "Marca"] if col in conversaciones.columns]
        merged = conversaciones.drop(columns=drop_cols, errors="ignore").merge(
            meta,
            on="clientId",
            how="left",
            validate="one_to_one",
        )
    else:
        cols = ["clientId", "createdAt", "subProjectInfo"]
        if has_marca:
            cols.append("Marca")

        project_map = df_raw[cols].copy()
        project_map["createdAt"] = pd.to_datetime(project_map["createdAt"], errors="coerce")
        project_map["subProjectInfo"] = project_map["subProjectInfo"].astype(str).str.strip()
        if has_marca:
            project_map["Marca"] = project_map["Marca"].astype(str).str.strip()

        project_map = project_map[
            project_map["subProjectInfo"].notna()
            & (project_map["subProjectInfo"] != "")
            & (project_map["subProjectInfo"] != "Sin Proyecto")
        ]
        group_cols = ["clientId", "subProjectInfo"] + (["Marca"] if has_marca else [])
        project_map = (
            project_map.sort_values("createdAt")
            .groupby(group_cols, as_index=False)
            .agg(createdAt=("createdAt", "min"))
        )
        merged = conversaciones[["clientId", "summary"]].copy().merge(
            project_map,
            on="clientId",
            how="left",
            validate="one_to_many",
        )

    df_out = pd.DataFrame([_record_from_summary(row) for _, row in merged.iterrows()])
    if df_out.empty:
        return pd.DataFrame(columns=list(INSIGHT_COLUMNS.keys()))
    df_out["createdAt"] = pd.to_datetime(df_out["createdAt"], errors="coerce")
    return df_out

