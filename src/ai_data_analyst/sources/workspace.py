import io
import re
from pathlib import Path
from tempfile import NamedTemporaryFile

import duckdb
import pandas as pd

_IDENTIFIER_PATTERN = re.compile(r"[^0-9A-Za-z_]+")


def quote_identifier(value: str) -> str:
    return '"' + value.replace('"', '""') + '"'


def sanitize_name(value: str) -> str:
    cleaned = _IDENTIFIER_PATTERN.sub("_", value).strip("_") or "table"
    if not re.match(r"^[A-Za-z_]", cleaned):
        cleaned = f"t_{cleaned}"
    return cleaned


class DataWorkspace:
    """In-memory analytical workspace with file-backed source adapters."""

    def __init__(self, connection=None, max_upload_bytes: int = 50_000_000):
        self.connection = connection or duckdb.connect(database=":memory:")
        self.tables: list[str] = []
        self.max_upload_bytes = max_upload_bytes
        self._temporary_paths: list[Path] = []
        self._schema_cache: str | None = None

    def close(self) -> None:
        try:
            self.connection.close()
        except Exception:
            pass
        for temporary_path in self._temporary_paths:
            temporary_path.unlink(missing_ok=True)
        self._temporary_paths.clear()
        self.tables = []
        self._schema_cache = None

    def register_frame(self, table_name: str, frame: pd.DataFrame) -> None:
        table_name = self._unique_name(sanitize_name(table_name), set(self.tables))
        token = "_pandas_ingest"
        self.connection.register(token, frame)
        try:
            self.connection.execute(
                f"CREATE OR REPLACE TABLE {quote_identifier(table_name)} AS SELECT * FROM {token}"
            )
        finally:
            try:
                self.connection.unregister(token)
            except Exception:
                pass
        self.tables.append(table_name)
        self._schema_cache = None

    def load_uploads(self, uploads) -> None:
        self.close()
        self.connection = duckdb.connect(database=":memory:")
        seen: set[str] = set()
        for upload in uploads or []:
            self._ensure_upload_size(upload)
            stem = sanitize_name(Path(upload.name).stem)
            suffix = Path(upload.name).suffix.lower()
            if suffix == ".csv":
                table_name = self._unique_name(stem, seen)
                self._load_csv(table_name, upload.getvalue())
                seen.add(table_name)
            elif suffix == ".xlsx":
                data = upload.getvalue()
                workbook = pd.ExcelFile(io.BytesIO(data), engine="openpyxl")
                for sheet in workbook.sheet_names:
                    table_name = self._unique_name(sanitize_name(f"{stem}_{sheet}"), seen)
                    self.register_frame(table_name, workbook.parse(sheet))
                    seen.add(table_name)
            elif suffix == ".xls":
                raise ValueError("Legacy .xls files are not supported; save the workbook as .xlsx.")
            else:
                raise ValueError(f"Unsupported upload type: {suffix}")

    def load_database(self, upload) -> None:
        self.close()
        suffix = Path(upload.name).suffix.lower()
        self._ensure_upload_size(upload)
        if suffix == ".duckdb":
            temporary_path = self._write_temp(upload, suffix)
            self.connection = duckdb.connect(database=str(temporary_path), read_only=True)
            self.tables = [row[0] for row in self.connection.sql("SHOW TABLES").fetchall()]
            return
        if suffix not in {".db", ".sqlite", ".sqlite3"}:
            raise ValueError("Supported database files are .duckdb, .db, .sqlite, and .sqlite3.")
        temporary_path = self._write_temp(upload, suffix)
        self.connection = duckdb.connect(database=":memory:")
        if not self._load_sqlite_native(temporary_path):
            self._load_sqlite_pandas(temporary_path)

    def columns(self, table_name: str) -> list[dict[str, str]]:
        rows = self.connection.sql(
            f"DESCRIBE SELECT * FROM {quote_identifier(table_name)}"
        ).fetchall()
        return [{"name": row[0], "dtype": str(row[1])} for row in rows]

    def row_count(self, table_name: str) -> int:
        row = self.connection.sql(f"SELECT COUNT(*) FROM {quote_identifier(table_name)}").fetchone()
        return int(row[0]) if row else 0

    def missing_value_count(self, table_name: str) -> int:
        columns = self.columns(table_name)
        if not columns:
            return 0
        expression = " + ".join(
            f"COUNT(*) FILTER (WHERE {quote_identifier(column['name'])} IS NULL)" for column in columns
        )
        row = self.connection.sql(
            f"SELECT {expression} FROM {quote_identifier(table_name)}"
        ).fetchone()
        return int(row[0]) if row else 0

    def frame(self, table_name: str, limit: int | None = None) -> pd.DataFrame:
        query = f"SELECT * FROM {quote_identifier(table_name)}"
        if limit is not None:
            query += f" LIMIT {int(limit)}"
        return self.connection.sql(query).df()

    def schema_text(self, include_samples: bool = True) -> str:
        if include_samples and self._schema_cache is not None:
            return self._schema_cache
        built = self._compose_schema(include_samples=include_samples)
        if include_samples:
            self._schema_cache = built
        return built

    def _compose_schema(self, include_samples: bool) -> str:
        blocks = []
        for table in self.tables:
            lines = [f"{table}:"]
            lines.extend(f"  - {column['name']}: {column['dtype']}" for column in self.columns(table))
            if include_samples:
                sample = self.frame(table, limit=3)
                if not sample.empty:
                    lines.append(f"  sample_rows: {sample.to_dict(orient='records')}")
            blocks.append("\n".join(lines))
        return "\n\n".join(blocks)

    def _load_csv(self, table_name: str, data: bytes) -> None:
        temporary_file = NamedTemporaryFile(suffix=".csv", delete=False)
        try:
            temporary_file.write(data)
            temporary_file.flush()
            temporary_path = Path(temporary_file.name)
        finally:
            temporary_file.close()
        escaped = str(temporary_path).replace("'", "''")
        try:
            self.connection.execute(
                f"CREATE TABLE {quote_identifier(table_name)} AS "
                f"SELECT * FROM read_csv_auto('{escaped}')"
            )
        finally:
            temporary_path.unlink(missing_ok=True)
        self.tables.append(table_name)
        self._schema_cache = None

    def _load_sqlite_native(self, path: Path) -> bool:
        escaped = str(path).replace("'", "''")
        try:
            self.connection.execute(f"ATTACH '{escaped}' AS sqlite_src (TYPE SQLITE)")
            tables = self.connection.sql(
                """
                SELECT table_name
                FROM information_schema.tables
                WHERE table_catalog = 'sqlite_src' OR table_schema = 'sqlite_src'
                """
            ).fetchall()
            if not tables:
                tables = [
                    (row[0],)
                    for row in self.connection.sql("SHOW TABLES FROM sqlite_src").fetchall()
                ]
            for (name,) in tables:
                table_name = self._unique_name(sanitize_name(name), set(self.tables))
                self.connection.execute(
                    f"CREATE TABLE {quote_identifier(table_name)} AS "
                    f"SELECT * FROM sqlite_src.{quote_identifier(name)}"
                )
                self.tables.append(table_name)
            self.connection.execute("DETACH sqlite_src")
            return bool(self.tables)
        except Exception:
            try:
                self.connection.execute("DETACH sqlite_src")
            except Exception:
                pass
            self.tables = []
            return False

    def _load_sqlite_pandas(self, path: Path) -> None:
        import sqlite3

        with sqlite3.connect(path) as sqlite_connection:
            names = sqlite_connection.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name NOT LIKE 'sqlite_%'"
            ).fetchall()
            for (name,) in names:
                table_name = self._unique_name(sanitize_name(name), set(self.tables))
                frame = pd.read_sql_query(f"SELECT * FROM {quote_identifier(name)}", sqlite_connection)
                self.register_frame(table_name, frame)

    def _ensure_upload_size(self, upload) -> None:
        size = getattr(upload, "size", None)
        if size is None:
            size = len(upload.getvalue())
        if int(size) > self.max_upload_bytes:
            raise ValueError(
                f"File exceeds the {self.max_upload_bytes:,} byte upload limit."
            )

    def _write_temp(self, upload, suffix: str) -> Path:
        temporary_file = NamedTemporaryFile(suffix=suffix, delete=False)
        try:
            temporary_file.write(upload.getvalue())
            temporary_file.flush()
            temporary_path = Path(temporary_file.name)
        finally:
            temporary_file.close()
        self._temporary_paths.append(temporary_path)
        return temporary_path

    @staticmethod
    def _unique_name(base: str, seen: set[str]) -> str:
        candidate = base
        suffix = 2
        while candidate in seen:
            candidate = f"{base}_{suffix}"
            suffix += 1
        return candidate
