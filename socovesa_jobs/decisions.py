from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from .state import AgentState


def decide_next_action(state: AgentState) -> str:
    if state.terminal_error:
        return "save_all"
    if state.df is None:
        return "load"
    if state.conversaciones is None:
        return "preprocess"
    if not state.compress_done:
        return "compress"
    if state.insights_df is None:
        return "build_insights_df"
    if state.aggregates is None:
        return "build_aggregates"
    if not state.historical_context:
        return "load_historical_context"
    if not state.weekly_comparison:
        return "build_weekly_comparison"
    if state.general_insights is None:
        return "generate_general"
    if state.validation_attempts == 0:
        return "validate_general"
    if not state.tendencias_done:
        return "generate_tendencias"
    if not state.subprojects_done:
        return "generate_subproject"
    if not state.marcas_done:
        return "generate_marca"
    return "save_all"


def decide_compression_config(metrics: dict[str, float]) -> dict[str, Any]:
    null_pct = metrics.get("null_pct", 0.0)
    avg_text_length = metrics.get("avg_text_length", 0.0)
    if null_pct > 0.20:
        return {"max_retries": 5, "temperature": 0.1, "reasoning": "high null rate"}
    if avg_text_length > 500:
        return {"max_retries": 4, "temperature": 0.15, "reasoning": "long conversations"}
    return {"max_retries": 3, "temperature": 0.0, "reasoning": "standard quality"}


def decide_parallelization(state: AgentState) -> dict[str, Any]:
    df = state.insights_df
    if df is None or df.empty:
        return {"parallelize_subprojects": False, "parallelize_marcas": False, "max_workers": 1}

    total_rows = len(df)
    subprojects = df["subProjectInfo"].nunique() if "subProjectInfo" in df.columns else 0
    marcas = df["Marca"].nunique() if "Marca" in df.columns else 0
    max_workers = 4 if total_rows > 1000 else 2
    return {
        "parallelize_subprojects": subprojects > 5 and total_rows > 500,
        "parallelize_marcas": marcas > 5 and total_rows > 500,
        "max_workers": max_workers,
    }
