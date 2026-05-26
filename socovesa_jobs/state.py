from __future__ import annotations

import json
from dataclasses import dataclass, field
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    import pandas as pd


@dataclass
class AgentState:
    label: str
    step: int = 0

    df: pd.DataFrame | None = None
    conversaciones: pd.DataFrame | None = None
    insights_df: pd.DataFrame | None = None

    quality_metrics: dict[str, float] = field(default_factory=dict)
    aggregates: dict[str, Any] | None = None

    compression_strategy: dict[str, Any] = field(default_factory=dict)
    parallelization_strategy: dict[str, Any] = field(default_factory=dict)

    general_insights: str | None = None
    tendencias_insights: dict[str, str] = field(default_factory=dict)
    subproject_insights: dict[str, str] = field(default_factory=dict)
    marca_insights: dict[str, str] = field(default_factory=dict)

    validation_attempts: int = 0
    errors: list[str] = field(default_factory=list)
    decisions_made: list[str] = field(default_factory=list)

    historical_context: dict[str, Any] = field(default_factory=dict)
    weekly_comparison: dict[str, Any] = field(default_factory=dict)

    compress_done: bool = False
    tendencias_done: bool = False
    subprojects_done: bool = False
    marcas_done: bool = False
    terminal_error: bool = False

    def add_error(self, message: str, terminal: bool = False) -> None:
        self.errors.append(message)
        if terminal:
            self.terminal_error = True

    def to_context(self) -> str:
        return json.dumps(
            {
                "step": self.step,
                "label": self.label,
                "data_loaded": self.df is not None,
                "data_size": len(self.df) if self.df is not None else 0,
                "quality_metrics": self.quality_metrics,
                "conversations_processed": len(self.conversaciones) if self.conversaciones is not None else 0,
                "insights_df_size": len(self.insights_df) if self.insights_df is not None else 0,
                "compression_strategy": self.compression_strategy,
                "parallelization_strategy": self.parallelization_strategy,
                "general_insights_generated": self.general_insights is not None,
                "tendencias_done": self.tendencias_done,
                "subprojects_done": self.subprojects_done,
                "marcas_done": self.marcas_done,
                "validation_attempts": self.validation_attempts,
                "errors": self.errors[-3:],
            },
            indent=2,
            ensure_ascii=False,
        )
