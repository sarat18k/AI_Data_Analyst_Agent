from time import perf_counter

from ai_data_analyst.models import ExecutionResult, cap_result_rows
from ai_data_analyst.sources.workspace import DataWorkspace
from ai_data_analyst.validation.python import execute_python


class PythonExecutor:
    def __init__(self, workspace: DataWorkspace, max_rows: int):
        self.workspace = workspace
        self.max_rows = max_rows

    def execute(self, code: str) -> ExecutionResult:
        started = perf_counter()
        frames = {table: self.workspace.frame(table) for table in self.workspace.tables}
        rows, truncated = cap_result_rows(execute_python(code, frames), self.max_rows)
        return ExecutionResult(
            mode="python",
            code=code,
            rows=rows,
            row_count=len(rows),
            truncated=truncated,
            duration_ms=round((perf_counter() - started) * 1000, 2),
        )
