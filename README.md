# AI Data Analyst Agent

A Streamlit data analyst agent that accepts tabular files, answers questions in plain English, generates verified SQL or Python analysis, and returns insights, result tables, and charts.

## Current capabilities

- Upload CSV or XLSX files.
- Load local SQLite and DuckDB database files.
- Register uploaded data in DuckDB for cross-table analysis.
- Use OpenAI to choose SQL or Python analysis in a structured JSON response.
- Validate SQL as a single read-only query against known tables.
- Execute restricted Python analysis that must assign its output to `result`.
- Return an answer, evidence-based insights, caveats, generated code, and Plotly visuals.
- Limit result rows and bound the result data sent to OpenAI for summarization.
- Cache repeated analyses within the active session and retain result tables, charts, and code in history.
- Preview large tables with database-side counts and row limits instead of loading full datasets into the UI.
- Use built-in demo data without uploading files.

## Setup

```powershell
python -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
```

Copy `.env.example` to `.env` and add your key:

```text
OPENAI_API_KEY=your-key-here
OPENAI_MODEL=gpt-4o-mini
MAX_RESULT_ROWS=1000
MAX_PROMPT_ROWS=50
MAX_PREVIEW_ROWS=200
MAX_UPLOAD_BYTES=50000000
OPENAI_TIMEOUT_SECONDS=60
```

Never commit `.env` or expose an API key in screenshots, logs, or source control. Use a newly generated key if an existing key has been shared or exposed.

Run the app:

```powershell
streamlit run app.py
```

## Example questions

- What is the total revenue by customer?
- Which customer spent the most?
- Show monthly order totals.
- Which region has the highest average order value?
- Calculate the correlation between order amount and customer activity.

## Architecture

```text
CSV / Excel / SQLite / DuckDB
        -> source catalog and schema summary
        -> OpenAI structured analysis plan
        -> SQL validator or restricted Python runner
        -> DuckDB / Pandas execution
        -> bounded result summary
        -> answer, insights, caveats, table, and Plotly chart
```

The package is organized by responsibility:

- `app.py` - thin Streamlit launcher
- `src/ai_data_analyst/ui` - presentation layer
- `src/ai_data_analyst/sources` - file adapters and schema workspace
- `src/ai_data_analyst/planning` - OpenAI planning and synthesis
- `src/ai_data_analyst/validation` - generated-code validation
- `src/ai_data_analyst/execution` - deterministic SQL/Python execution
- `src/ai_data_analyst/services` - application orchestration
- `tests` - unit and boundary tests

## Safety and limitations

SQL is parsed as a single `SELECT` or `WITH` statement, checked against known tables, and blocked from write operations and file-scanning functions. The validator is intentionally conservative but is not a substitute for a separate production sandbox.

Python execution is restricted in-process. Imports, filesystem access, network access, subprocesses, private attributes, and arbitrary function calls are blocked. A production deployment should run generated code in an isolated worker or container with resource limits.

Schema metadata and bounded result rows are sent to OpenAI. Do not upload sensitive data unless your organization has approved that data flow. Remote PostgreSQL/MySQL connectors, authentication, persistence, and multi-user deployment are not included yet.

## Tests

```powershell
python -m pytest -q
ruff check .
```
