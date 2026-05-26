from __future__ import annotations

import pandas as pd


UNKNOWN_VALUES = {"desconocido", "desconocidos", "none", "nan", ""}


def pct(series: pd.Series, value: str) -> float:
    if len(series) == 0:
        return 0.0
    normalized = series.dropna().astype(str).str.lower().str.strip()
    return round(float((normalized == value).mean()), 4)


def dist(series: pd.Series, drop_unknown: bool = True) -> list[dict]:
    normalized = series.dropna().astype(str).str.lower().str.strip()
    if drop_unknown:
        normalized = normalized[~normalized.isin(UNKNOWN_VALUES)]
    total = len(normalized)
    if total == 0:
        return []
    counts = normalized.value_counts()
    return [
        {"categoria": cat, "conteo": int(count), "porcentaje": round(float(count / total), 4)}
        for cat, count in counts.items()
    ]


def project_top_k(series: pd.Series, k: int = 10) -> list[dict]:
    normalized = series.dropna().astype(str).str.strip()
    normalized = normalized[~normalized.isin(["", "Sin Proyecto", "nan", "None", "desconocido"])]
    total = len(normalized)
    if total == 0:
        return []
    return [
        {"proyecto": project, "conteo": int(count), "porcentaje": round(float(count / total), 4)}
        for project, count in normalized.value_counts().head(k).items()
    ]


def affinity(df: pd.DataFrame, k: int = 10) -> list[dict]:
    required = {"producto_origen", "producto_destino"}
    if not required.issubset(df.columns):
        return []

    tmp = df.copy()
    tmp["producto_origen"] = tmp["producto_origen"].fillna("desconocido").astype(str).str.strip()
    tmp["producto_destino"] = tmp["producto_destino"].fillna("desconocido").astype(str).str.strip()
    tmp = tmp[
        (tmp["producto_origen"] != "desconocido")
        & (tmp["producto_destino"] != "desconocido")
    ]
    if tmp.empty:
        return []

    counts = (
        tmp.groupby(["producto_origen", "producto_destino"])
        .size()
        .reset_index(name="conteo")
        .sort_values("conteo", ascending=False)
        .head(k)
    )
    total = counts["conteo"].sum()
    return [
        {
            "producto_origen": row["producto_origen"],
            "producto_destino": row["producto_destino"],
            "conteo": int(row["conteo"]),
            "porcentaje_movimiento": round(float(row["conteo"] / total), 4),
        }
        for _, row in counts.iterrows()
    ]


def build_project_aggregates(df: pd.DataFrame) -> dict:
    if df.empty:
        return {"total_conversaciones": 0}

    return {
        "total_conversaciones": int(df["clientId"].nunique()),
        "sentimiento": {
            "positivo": pct(df["sentimiento"], "positivo"),
            "neutral": pct(df["sentimiento"], "neutral"),
            "negativo": pct(df["sentimiento"], "negativo"),
        },
        "funnel": {
            "abandono_temprano_pct": pct(df["abandono"], "si"),
            "etapas_funnel": dist(df["etapa_funnel"]),
            "intencion_compra": dist(df["intencion_compra"]),
        },
        "conversion": {
            "tasa_conversion_lead": pct(df["derivado_vendedor"], "si"),
            "tasa_respuesta_recomendador": pct(df["respuesta_recomendador"], "si"),
        },
        "financiamiento": {"porcentaje_sin_pie": pct(df["sin_pie"], "si")},
        "pain_points": dist(df["pain_point"]),
        "motivos_abandono": dist(df.loc[df["abandono"] == "si", "motivo_abandono"]),
        "segmentos_cliente": dist(df["perfil_cliente"]),
        "situacion_laboral": dist(df["situacion_laboral"]),
        "ingreso": dist(df["ingreso"]),
        "capacidad_entrega_informacion": dist(df["capacidad_info"]),
        "topicos_consulta": dist(df["topicos_consulta"]),
        "tipo_consulta": dist(df["tipo_consulta"]),
        "atributos_valorados": dist(df["atributo_valorado"]),
        "topicos_valorados": dist(df["topico_valorado"]),
        "soluciones_bot_mas_usadas": dist(df["solucion_bot"]),
        "fricciones_bot": dist(df["friccion_bot"]),
        "demandas_no_cubiertas": dist(df["demanda_no_cubierta"]),
        "informacion_complementaria_requerida": dist(df["info_complementaria"]),
        "duda_recurrente": dist(df["duda_recurrente"]),
        "proyectos": {
            "mas_consultados": project_top_k(df["subProjectInfo"]),
            "afinidad_productos": affinity(df),
        },
    }

