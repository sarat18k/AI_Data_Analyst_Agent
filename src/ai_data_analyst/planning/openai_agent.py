import json
import logging

from openai import OpenAI

from ai_data_analyst.config import Settings
from ai_data_analyst.models import AnalysisPlan, AnalysisSummary
from ai_data_analyst.validation.sql import validate_sql

logger = logging.getLogger(__name__)

History = list[dict[str, str]] | None


class OpenAIAnalyst:
    """OpenAI adapter that returns validated, application-owned contracts."""

    def __init__(self, settings: Settings, client=None):
        self.settings = settings
        self.client = client

    def _client(self):
        self.settings.require_openai()
        if self.client is None:
            self.client = OpenAI(
                api_key=self.settings.openai_api_key,
                timeout=self.settings.openai_timeout_seconds,
            )
        return self.client

    def _json_response(self, messages: list[dict[str, str]]) -> dict:
        response = self._client().chat.completions.create(
            model=self.settings.openai_model,
            messages=messages,
            temperature=0,
            response_format={"type": "json_object"},
        )
        usage = getattr(response, "usage", None)
        if usage is not None:
            logger.info(
                "openai model=%s prompt_tokens=%s completion_tokens=%s",
                self.settings.openai_model,
                getattr(usage, "prompt_tokens", None),
                getattr(usage, "completion_tokens", None),
            )
        content = response.choices[0].message.content or "{}"
        try:
            return json.loads(content)
        except json.JSONDecodeError as exc:
            raise RuntimeError("OpenAI returned invalid structured JSON.") from exc

    def _with_history(self, messages: list[dict[str, str]], history: History) -> list[dict[str, str]]:
        combined = list(messages)
        for turn in (history or [])[-8:]:
            role = turn.get("role")
            content = turn.get("content")
            if role in {"user", "assistant"} and content:
                combined.append({"role": str(role), "content": str(content)[:4000]})
        return combined

    def plan(self, question: str, schema: str, tables: list[str], history: History = None) -> AnalysisPlan:
        payload = self._json_response(
            self._with_history(
                [
                    {
                        "role": "system",
                        "content": (
                            "Return JSON with keys mode, sql, python_code. "
                            "Choose mode sql for filtering, grouping, joining, totals, and trends. "
                            "Choose mode python for statistics or calculations SQL cannot express simply. "
                            "SQL must be one read-only DuckDB SELECT/WITH query using known tables. "
                            "For DuckDB strftime, use strftime(date_expression, '%Y-%m'), "
                            "not the SQLite argument order; "
                            "cast VARCHAR dates with TRY_CAST(date_expression AS TIMESTAMP). "
                            "Python must use supplied pandas DataFrames and assign final output to result. "
                            "Do not import modules or access files or networks."
                        ),
                    },
                    {"role": "user", "content": f"Schema:\n{schema}\n\nTables: {tables}"},
                ],
                history,
            )
            + [{"role": "user", "content": f"Question: {question}"}]
        )
        mode = str(payload.get("mode", "sql")).lower()
        if mode == "python":
            return AnalysisPlan(mode="python", code=str(payload.get("python_code", "")))
        return AnalysisPlan(
            mode="sql",
            code=validate_sql(str(payload.get("sql", "")), allowed_tables=tables),
        )

    def summarize(self, question: str, records: list[dict]) -> AnalysisSummary:
        payload = self._json_response([
            {
                "role": "system",
                "content": (
                    "Return JSON with keys answer, insights, caveats. Answer must be concise and direct. "
                    "Insights and caveats must be arrays of short strings. Use only the supplied computed "
                    "rows; "
                    "do not invent facts."
                ),
            },
            {"role": "user", "content": f"Question: {question}\nComputed result rows: {records}"},
        ])
        return AnalysisSummary(
            answer=str(payload.get("answer", "No answer was returned.")),
            insights=[str(item) for item in payload.get("insights", [])],
            caveats=[str(item) for item in payload.get("caveats", [])],
        )

    def repair_sql(
        self,
        question: str,
        sql: str,
        error: str,
        schema: str,
        tables: list[str],
        history: History = None,
    ) -> AnalysisPlan:
        payload = self._json_response(
            self._with_history(
                [
                    {
                        "role": "system",
                        "content": (
                            "Repair the supplied DuckDB query. Return JSON with exactly one key, sql. "
                            "Return one read-only SELECT or WITH query using only known tables. "
                            "Respect DuckDB syntax and cast VARCHAR dates before date functions."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Question: {question}\nSchema:\n{schema}\nTables: {tables}\n"
                            f"Failed SQL:\n{sql}\nExecution error:\n{error}"
                        ),
                    },
                ],
                history,
            )
        )
        return AnalysisPlan(
            mode="sql",
            code=validate_sql(str(payload.get("sql", "")), allowed_tables=tables),
        )

    def repair_python(
        self,
        question: str,
        code: str,
        error: str,
        schema: str,
        tables: list[str],
        history: History = None,
    ) -> AnalysisPlan:
        payload = self._json_response(
            self._with_history(
                [
                    {
                        "role": "system",
                        "content": (
                            "Repair the supplied pandas analysis. "
                            "Return JSON with exactly one key, python_code. "
                            "Use only the supplied DataFrames, do not import modules, and assign the final "
                            "DataFrame or value to result."
                        ),
                    },
                    {
                        "role": "user",
                        "content": (
                            f"Question: {question}\nSchema:\n{schema}\nTables: {tables}\n"
                            f"Failed Python:\n{code}\nExecution error:\n{error}"
                        ),
                    },
                ],
                history,
            )
        )
        return AnalysisPlan(mode="python", code=str(payload.get("python_code", "")))
