from dataclasses import dataclass, field
from typing import Literal

import pandas as pd

AnalysisMode = Literal["sql", "python"]


def cap_result_rows(frame: pd.DataFrame, max_rows: int) -> tuple[pd.DataFrame, bool]:
    """Keep at most max_rows, reporting whether additional rows were dropped."""
    limit = int(max_rows)
    truncated = len(frame) > limit
    return (frame.iloc[:limit].copy() if truncated else frame, truncated)


@dataclass(frozen=True)
class AnalysisPlan:
    mode: AnalysisMode
    code: str


@dataclass(frozen=True)
class AnalysisSummary:
    answer: str
    insights: list[str] = field(default_factory=list)
    caveats: list[str] = field(default_factory=list)


@dataclass(frozen=True)
class ExecutionResult:
    mode: AnalysisMode
    code: str
    rows: pd.DataFrame
    row_count: int
    truncated: bool = False
    duration_ms: float = 0.0
    validation_status: str = "Validated"
