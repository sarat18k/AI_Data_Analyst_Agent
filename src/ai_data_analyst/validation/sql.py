import re

import sqlglot
from sqlglot import exp
from sqlglot.errors import ParseError

FORBIDDEN_SQL = re.compile(
    r"\b(ALTER|ATTACH|CALL|COPY|CREATE|DELETE|DROP|EXPORT|GRANT|INSERT|INSTALL|LOAD|MERGE|PRAGMA|REPLACE|RESET|UPDATE|USE)\b",
    flags=re.IGNORECASE,
)
REVERSED_STRFTIME = re.compile(
    r"strftime\(\s*(['\"])([^'\"]+)\1\s*,\s*([A-Za-z_][\w$]*(?:\.[A-Za-z_][\w$]*)?)\s*\)",
    flags=re.IGNORECASE,
)
DATE_FIRST_STRFTIME = re.compile(
    r"strftime\(\s*([A-Za-z_][\w$]*(?:\.[A-Za-z_][\w$]*)?)\s*,\s*(['\"])([^'\"]+)\2\s*\)",
    flags=re.IGNORECASE,
)
DENIED_FUNCTIONS = {
    "copy",
    "glob",
    "read_blob",
    "read_csv",
    "read_csv_auto",
    "read_json",
    "read_json_auto",
    "read_ndjson",
    "read_parquet",
    "read_text",
    "read_xlsx",
    "sqlite_scan",
}
FILE_TABLE = re.compile(
    r"[\\/]|\.(csv|tsv|parquet|json|ndjson|xlsx|xls|duckdb|db|sqlite|sqlite3)$",
    re.IGNORECASE,
)


def normalize_duckdb_sql(sql: str) -> str:
    """Normalize common date-function syntax produced for other SQL dialects."""
    normalized = REVERSED_STRFTIME.sub(
        r"strftime(TRY_CAST(\3 AS TIMESTAMP), '\2')",
        sql,
    )
    return DATE_FIRST_STRFTIME.sub(
        r"strftime(TRY_CAST(\1 AS TIMESTAMP), '\3')",
        normalized,
    )


def _function_name(node: exp.Expression) -> str:
    if isinstance(node, exp.Anonymous):
        this = node.this
        return str(this).lower() if this is not None else ""
    name = getattr(node, "sql_name", lambda: "")()
    if name:
        return str(name).lower()
    return str(node.key or "").lower()


def validate_sql(sql: str, allowed_tables: list[str] | None = None) -> str:
    """Validate one conservative, read-only DuckDB statement."""
    normalized = normalize_duckdb_sql((sql or "").strip().rstrip(";").strip())
    if not normalized:
        raise ValueError("The model returned an empty SQL query.")
    if ";" in normalized:
        raise ValueError("Multiple SQL statements are not allowed.")
    if not re.match(r"^(SELECT|WITH)\b", normalized, flags=re.IGNORECASE):
        raise ValueError("Only SELECT and WITH queries are allowed.")
    try:
        parsed = sqlglot.parse_one(normalized, dialect="duckdb")
    except ParseError as exc:
        raise ValueError("SQL could not be parsed as a single read-only query.") from exc
    if parsed is None or not isinstance(parsed, (exp.Select, exp.Union, exp.Except, exp.Intersect)):
        raise ValueError("Only SELECT and WITH queries are allowed.")

    rendered = parsed.sql(dialect="duckdb", comments=False)
    forbidden = FORBIDDEN_SQL.search(rendered)
    if forbidden:
        raise ValueError(f"SQL keyword is not allowed: {forbidden.group(1).upper()}.")

    for node in parsed.find_all(exp.Func, exp.Anonymous):
        name = _function_name(node)
        if name in DENIED_FUNCTIONS:
            raise ValueError(f"SQL function is not allowed: {name}.")

    cte_names = {cte.alias_or_name.lower() for cte in parsed.find_all(exp.CTE)}
    referenced: set[str] = set()
    for table in parsed.find_all(exp.Table):
        name = table.name or ""
        if not name:
            continue
        if FILE_TABLE.search(name):
            raise ValueError("File scanning is not allowed in SQL.")
        if name.lower() in cte_names:
            continue
        referenced.add(name.lower())

    if allowed_tables is not None:
        known = {table.lower() for table in allowed_tables}
        unknown = sorted(referenced - known)
        if unknown:
            raise ValueError(f"Unknown table(s): {', '.join(unknown)}.")
    return normalized
