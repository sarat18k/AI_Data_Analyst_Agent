from time import perf_counter

from ai_data_analyst.models import ExecutionResult, cap_result_rows
from ai_data_analyst.sources.workspace import DataWorkspace
from ai_data_analyst.validation.sql import validate_sql


class SQLExecutor:
    def __init__(self, workspace: DataWorkspace, max_rows: int):
        self.workspace = workspace
        self.max_rows = max_rows

    def execute(self, sql: str) -> ExecutionResult:
        started = perf_counter()
        validated = validate_sql(sql, self.workspace.tables)
        fetch_limit = int(self.max_rows) + 1
        wrapped = f"SELECT * FROM ({validated}) AS analyst_result LIMIT {fetch_limit}"
        rows, truncated = cap_result_rows(self.workspace.connection.sql(wrapped).df(), self.max_rows)
        return ExecutionResult(
            mode="sql",
            code=validated,
            rows=rows,
            row_count=len(rows),
            truncated=truncated,
            duration_ms=round((perf_counter() - started) * 1000, 2),
        )
