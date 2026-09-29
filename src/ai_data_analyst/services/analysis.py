import inspect
from collections import OrderedDict

from ai_data_analyst.config import Settings
from ai_data_analyst.execution.python import PythonExecutor
from ai_data_analyst.execution.sql import SQLExecutor
from ai_data_analyst.models import ExecutionResult
from ai_data_analyst.planning.openai_agent import OpenAIAnalyst
from ai_data_analyst.sources.workspace import DataWorkspace

History = list[dict[str, str]] | None


def _call_with_history(method, *args, history: History = None, **kwargs):
    try:
        parameters = inspect.signature(method).parameters
    except (TypeError, ValueError):
        return method(*args, **kwargs)
    if "history" in parameters or any(
        parameter.kind is inspect.Parameter.VAR_KEYWORD for parameter in parameters.values()
    ):
        return method(*args, history=history, **kwargs)
    return method(*args, **kwargs)


class AnalysisService:
    """Coordinates planning, deterministic execution, and result synthesis."""

    def __init__(self, workspace: DataWorkspace, settings: Settings | None = None, analyst=None):
        self.workspace = workspace
        self.settings = settings or Settings.from_environment()
        self.analyst = analyst or OpenAIAnalyst(self.settings)
        self._cache: OrderedDict[tuple, tuple[ExecutionResult, object]] = OrderedDict()

    def execute(self, question: str, history: History = None) -> ExecutionResult:
        plan = _call_with_history(
            self.analyst.plan,
            question,
            self.workspace.schema_text(),
            self.workspace.tables,
            history=history,
        )
        if plan.mode == "python":
            executor = PythonExecutor(self.workspace, self.settings.max_result_rows)
            try:
                return executor.execute(plan.code)
            except Exception as first_error:
                repair = _call_with_history(
                    self.analyst.repair_python,
                    question,
                    plan.code,
                    str(first_error),
                    self.workspace.schema_text(),
                    self.workspace.tables,
                    history=history,
                )
                return executor.execute(repair.code)
        executor = SQLExecutor(self.workspace, self.settings.max_result_rows)
        try:
            return executor.execute(plan.code)
        except Exception as first_error:
            repair = _call_with_history(
                self.analyst.repair_sql,
                question,
                plan.code,
                str(first_error),
                self.workspace.schema_text(),
                self.workspace.tables,
                history=history,
            )
            return executor.execute(repair.code)

    def summarize(self, question: str, execution: ExecutionResult):
        records = execution.rows.head(self.settings.max_prompt_rows).to_dict(orient="records")
        return self.analyst.summarize(question, records)

    def analyze(self, question: str, history: History = None):
        cache_key = (
            question.strip(),
            self.workspace.schema_text(),
            tuple((item.get("role"), item.get("content")) for item in (history or [])[-8:]),
        )
        cached = self._cache.get(cache_key)
        if cached is not None:
            self._cache.move_to_end(cache_key)
            return cached
        execution = self.execute(question, history)
        summary = self.summarize(question, execution)
        self._cache[cache_key] = (execution, summary)
        while len(self._cache) > 32:
            self._cache.popitem(last=False)
        return execution, summary
