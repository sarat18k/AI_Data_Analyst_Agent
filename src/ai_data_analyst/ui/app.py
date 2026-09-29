import html

import pandas as pd
import streamlit as st

from ai_data_analyst.charts import auto_chart, build_chart
from ai_data_analyst.config import Settings
from ai_data_analyst.services.analysis import AnalysisService
from ai_data_analyst.sources.workspace import DataWorkspace

st.set_page_config(
    page_title="AI Data Analyst",
    page_icon=":material/analytics:",
    layout="wide",
    initial_sidebar_state="expanded",
)


def _apply_styles() -> None:
    st.markdown(
        """
        <style>
        :root {
            --ink: #172033;
            --muted: #687386;
            --line: #e2e6ec;
            --surface: #f6f7f9;
            --panel: #ffffff;
            --accent: #3157d5;
            --accent-soft: #eef2ff;
            --success: #08785c;
            --success-soft: #edf8f4;
        }
        html, body, [class*="css"] {
            font-family: Inter, ui-sans-serif, -apple-system, BlinkMacSystemFont, "Segoe UI", sans-serif;
        }
        .stApp { background: var(--surface); }
        .main .block-container {
            max-width: 1320px;
            padding-top: 2.25rem;
            padding-bottom: 4rem;
        }
        [data-testid="stSidebar"] {
            background: var(--panel);
            border-right: 1px solid var(--line);
        }
        [data-testid="stSidebar"] > div:first-child { padding-top: 1.5rem; }
        [data-testid="stSidebar"] h2 { color: var(--ink); font-size: .95rem; }
        h1, h2, h3 { color: var(--ink); letter-spacing: -.02em; }
        h1 { font-size: 2.2rem; line-height: 1.12; font-weight: 720; }
        h2 { font-size: 1.45rem; }
        h3 { font-size: 1.05rem; }
        .brand {
            display: flex; align-items: center; gap: .72rem;
            margin-bottom: .35rem;
        }
        .brand-mark {
            width: 2rem; height: 2rem; border-radius: 8px;
            display: grid; place-items: center;
            background: var(--ink); color: white;
            font-weight: 750; font-size: .82rem;
        }
        .brand-name { color: var(--ink); font-weight: 720; font-size: .98rem; }
        .brand-meta { color: var(--muted); font-size: .72rem; }
        .eyebrow {
            color: var(--accent); font-size: .72rem; font-weight: 700;
            letter-spacing: .1em; text-transform: uppercase;
        }
        .hero-copy {
            color: var(--muted); font-size: 1rem; line-height: 1.65;
            max-width: 46rem; margin-bottom: 1.35rem;
        }
        .source-card {
            background: var(--panel); border: 1px solid var(--line);
            border-radius: 12px; padding: 1rem 1.15rem;
            margin: .5rem 0 1rem;
        }
        .source-label {
            color: var(--muted); font-size: .78rem;
            text-transform: uppercase; letter-spacing: .07em; font-weight: 650;
        }
        .source-value { color: var(--ink); font-size: 1rem; font-weight: 680; margin-top: .2rem; }
        .question-panel {
            background: var(--accent-soft); border: 1px solid #dce3ff;
            border-radius: 12px; padding: 1rem 1.1rem .45rem;
            margin: 1.25rem 0 .8rem;
        }
        .question-panel p { color: var(--muted); margin-bottom: .75rem; }
        div[data-testid="stMetric"] {
            background: var(--panel); border: 1px solid var(--line);
            border-radius: 12px; padding: .85rem 1rem;
        }
        [data-testid="stMetricLabel"] { color: var(--muted); }
        [data-testid="stMetricValue"] { color: var(--ink); font-weight: 700; }
        div[data-testid="stChatMessage"] {
            background: var(--panel); border: 1px solid var(--line);
            border-radius: 14px; padding: .35rem .65rem; margin-bottom: .75rem;
        }
        button[kind="primary"] {
            background: var(--ink); border-color: var(--ink); color: white;
        }
        button[kind="primary"]:hover { background: #252f43; border-color: #252f43; }
        button[kind="secondary"] {
            background: var(--panel); border-color: var(--line); color: var(--ink);
        }
        [data-testid="stAlert"] { border-radius: 12px; border-width: 1px; }
        .insight-card {
            border-radius: 10px; padding: .9rem 1rem; min-height: 4.5rem;
            color: var(--ink); background: var(--panel);
            border: 1px solid var(--line); border-left: 3px solid var(--accent);
            line-height: 1.5;
        }
        .step-nav {
            background: var(--panel); border: 1px solid var(--line);
            border-radius: 12px; padding: .65rem; margin: 1rem 0 1.5rem;
        }
        .sidebar-workflow {
            background: var(--surface); border: 1px solid var(--line);
            border-radius: 10px; padding: .75rem; margin: .9rem 0 1rem;
        }
        .sidebar-workflow-title {
            color: var(--muted); font-size: .7rem; font-weight: 750;
            letter-spacing: .08em; text-transform: uppercase; margin-bottom: .6rem;
        }
        .step-caption { color: var(--muted); font-size: .82rem; margin: -.75rem 0 1rem; }
        .color-rule {
            background: var(--accent); border-radius: 999px;
            width: 2.5rem; height: 3px; margin: .6rem 0 1.15rem;
        }
        .page-kicker {
            color: var(--accent); font-size: .74rem; font-weight: 700;
            letter-spacing: .08em; text-transform: uppercase;
        }
        .preview-shell {
            background: var(--panel); border: 1px solid var(--line);
            border-radius: 12px; padding: .75rem;
        }
        [data-testid="stFileUploaderDropzone"] {
            background: var(--panel); border: 1px dashed #bfc7d5; border-radius: 12px;
        }
        [data-testid="stDataFrame"] { border-radius: 10px; overflow: hidden; }
        .stTabs [data-baseweb="tab-list"] { gap: 1.1rem; border-bottom: 1px solid var(--line); }
        .stTabs [data-baseweb="tab"] { padding-left: 0; padding-right: 0; }
        [data-testid="stChatInput"] { border-color: var(--line); }
        footer, #MainMenu { visibility: hidden; }
        </style>
        """,
        unsafe_allow_html=True,
    )


def _settings() -> Settings:
    if "settings" not in st.session_state:
        st.session_state.settings = Settings.from_environment()
    return st.session_state.settings


def _workspace() -> DataWorkspace:
    if "workspace" not in st.session_state:
        st.session_state.workspace = DataWorkspace(max_upload_bytes=_settings().max_upload_bytes)
    return st.session_state.workspace


def _analysis_service(workspace: DataWorkspace) -> AnalysisService:
    token = id(workspace)
    if st.session_state.get("analysis_service_token") != token:
        st.session_state.analysis_service = AnalysisService(workspace, settings=_settings())
        st.session_state.analysis_service_token = token
    return st.session_state.analysis_service


def _reset_workspace() -> None:
    workspace = _workspace()
    workspace.close()
    st.session_state.workspace = DataWorkspace(max_upload_bytes=_settings().max_upload_bytes)
    st.session_state.loaded_signature = None
    st.session_state.chat_history = []
    st.session_state.source_label = "No data loaded"
    st.session_state.is_demo = False
    st.session_state.current_page = "Load data"
    st.session_state.pop("analysis_service", None)
    st.session_state.pop("analysis_service_token", None)


def _load_demo() -> None:
    _workspace().close()
    workspace = DataWorkspace(max_upload_bytes=_settings().max_upload_bytes)
    customers = pd.DataFrame({
        "customer_id": [1, 2, 3, 4],
        "customer_name": ["Ava", "Leo", "Mia", "Noah"],
        "region": ["North", "South", "North", "West"],
    })
    orders = pd.DataFrame({
        "order_id": [101, 102, 103, 104],
        "customer_id": [1, 2, 1, 3],
        "amount": [120.5, 220.0, 150.25, 310.75],
        "order_date": ["2024-01-10", "2024-01-12", "2024-02-05", "2024-02-10"],
    })
    products = pd.DataFrame({
        "product_id": [10, 11, 12],
        "product_name": ["Laptop", "Mouse", "Monitor"],
        "category": ["Electronics", "Accessories", "Electronics"],
        "unit_price": [900.0, 25.0, 300.0],
    })
    for name, frame in (("customers", customers), ("orders", orders), ("products", products)):
        workspace.register_frame(name, frame)
    st.session_state.workspace = workspace
    st.session_state.loaded_signature = ("demo",)
    st.session_state.chat_history = []
    st.session_state.source_label = "Built-in commerce demo"
    st.session_state.is_demo = True
    st.session_state.current_page = "Analyze"
    st.session_state.pop("analysis_service", None)
    st.session_state.pop("analysis_service_token", None)


def _render_sidebar(workspace: DataWorkspace) -> None:
    with st.sidebar:
        st.markdown(
            '<div class="brand"><div class="brand-mark">AI</div><div>'
            '<div class="brand-name">Data Analyst</div>'
            '<div class="brand-meta">Trusted analysis workspace</div></div></div>',
            unsafe_allow_html=True,
        )
        st.caption("From source data to evidence-backed answers.")
        st.divider()
        if st.button("Load demo data", width="stretch"):
            _load_demo()
            st.rerun()
        if st.button("Clear data", width="stretch"):
            _reset_workspace()
            st.rerun()
        st.caption("CSV, XLSX, SQLite, and DuckDB files")
        _render_navigation(workspace, in_sidebar=True)
        if st.session_state.get("is_demo"):
            st.success("Demo workspace ready")
            st.caption("Quick questions")
            sidebar_questions = [
                "Total order value by customer",
                "Revenue by region",
                "Monthly order totals",
                "Customers with multiple orders",
            ]
            for index, question in enumerate(sidebar_questions):
                if st.button(question, key=f"sidebar_demo_question_{index}", width="stretch"):
                    st.session_state.selected_question = question
        if workspace.tables:
            st.subheader("Tables")
            for table in workspace.tables:
                with st.expander(table):
                    for column in workspace.columns(table):
                        st.caption(f"{column['name']} · {column['dtype']}")


def _render_header(workspace: DataWorkspace) -> None:
    source_label = st.session_state.get("source_label", "Uploaded data")
    total_rows = sum(workspace.row_count(table) for table in workspace.tables)
    total_columns = sum(len(workspace.columns(table)) for table in workspace.tables)
    st.markdown('<div class="eyebrow">OpenAI-powered analysis workspace</div>', unsafe_allow_html=True)
    st.markdown('<div class="color-rule"></div>', unsafe_allow_html=True)
    st.title("Ask your data better questions.")
    st.markdown(
        '<div class="hero-copy">Generate validated SQL or Python, inspect the evidence, '
        'and turn the result into a clear decision.</div>',
        unsafe_allow_html=True,
    )
    st.markdown(
        f'<div class="source-card"><div class="source-label">Active source</div>'
        f'<div class="source-value">{html.escape(str(source_label))}</div></div>',
        unsafe_allow_html=True,
    )
    metrics = st.columns(3)
    metrics[0].metric("Tables", len(workspace.tables))
    metrics[1].metric("Rows loaded", f"{total_rows:,}")
    metrics[2].metric("Columns", total_columns)


def _render_demo_questions() -> str | None:
    if not st.session_state.get("is_demo"):
        return None
    st.markdown(
        '<div class="question-panel"><h3>Start with a demo question</h3>'
        '<p>Choose a prompt or write your own below.</p></div>',
        unsafe_allow_html=True,
    )
    questions = [
        "What is the total order value by customer?",
        "Which region generated the most revenue?",
        "Show monthly order totals.",
        "Which customers have placed more than one order?",
    ]
    selected = None
    for index in range(0, len(questions), 2):
        columns = st.columns(2)
        for column, question in zip(columns, questions[index:index + 2], strict=True):
            if column.button(
                question,
                key=f"demo_question_{index}_{question}",
                width="stretch",
                type="primary",
            ):
                selected = question
    return selected


def _render_history() -> None:
    for index, message in enumerate(st.session_state.get("chat_history", [])):
        with st.chat_message(message["role"]):
            if message["role"] == "assistant" and message.get("execution") is not None:
                _render_execution(
                    message["execution"],
                    message["summary"],
                    key_prefix=f"history_{index}",
                )
            else:
                st.markdown(message["content"])


def _load_inputs(workspace: DataWorkspace) -> None:
    uploads = st.file_uploader(
        "Upload CSV or Excel files",
        type=["csv", "xlsx"],
        accept_multiple_files=True,
    )
    if uploads:
        signature = tuple((item.name, item.size, item.type) for item in uploads)
        if st.session_state.get("loaded_signature") != signature:
            workspace.load_uploads(uploads)
            st.session_state.loaded_signature = signature
            st.session_state.chat_history = []
            st.session_state.source_label = "Uploaded tabular files"
            st.session_state.is_demo = False
            st.session_state.current_page = "Analyze"
            st.toast("Data loaded. Opening Analyze.")
            st.rerun()

    database = st.file_uploader(
        "Or load a local SQLite/DuckDB database",
        type=["db", "sqlite", "sqlite3", "duckdb"],
    )
    if database:
        signature = (database.name, database.size, database.type)
        if st.session_state.get("loaded_signature") != signature:
            workspace.load_database(database)
            st.session_state.loaded_signature = signature
            st.session_state.chat_history = []
            st.session_state.source_label = f"Database: {database.name}"
            st.session_state.is_demo = False
            st.session_state.current_page = "Analyze"
            st.toast("Database loaded. Opening Analyze.")
            st.rerun()


def _render_navigation(workspace: DataWorkspace, in_sidebar: bool = False) -> str:
    pages = ["Load data", "Explore tables", "Analyze"]
    if not workspace.tables:
        st.session_state.current_page = "Load data"
    current_page = st.session_state.get("current_page", "Load data")
    container = st.sidebar if in_sidebar else st
    with container:
        if in_sidebar:
            st.markdown('<div class="sidebar-workflow">', unsafe_allow_html=True)
            st.markdown('<div class="sidebar-workflow-title">Workflow</div>', unsafe_allow_html=True)
        else:
            st.markdown('<div class="step-nav"><strong>Workflow</strong></div>', unsafe_allow_html=True)
        for index, page in enumerate(pages):
            label = f"{index + 1}  {page}"
            is_disabled = not workspace.tables and page != "Load data"
            button_type = "primary" if page == current_page else "secondary"
            if st.button(
                label,
                key=f"workflow_{'sidebar_' if in_sidebar else ''}{page.replace(' ', '_').lower()}",
                type=button_type,
                disabled=is_disabled,
                width="stretch",
            ):
                st.session_state.current_page = page
                st.rerun()
        if in_sidebar:
            st.markdown("</div>", unsafe_allow_html=True)
        status = (
            "Load data to unlock the next steps"
            if not workspace.tables
            else "Move through your analysis"
        )
        st.markdown(
            f'<div class="step-caption">Step {pages.index(current_page) + 1} of 3 · {status}</div>',
            unsafe_allow_html=True,
        )
    return current_page


def _render_data_page(workspace: DataWorkspace) -> None:
    st.markdown('<div class="page-kicker">Step 1 · Connect</div>', unsafe_allow_html=True)
    st.title("Start with a trusted data source")
    st.markdown(
        '<div class="hero-copy">Load a local dataset, inspect its structure, and ask questions '
        'in plain English. Your analysis remains grounded in the tables you choose.</div>',
        unsafe_allow_html=True,
    )
    intro_columns = st.columns([1, 1], gap="medium")
    with intro_columns[0]:
        st.markdown("#### Explore with sample data")
        st.caption("Use the built-in commerce dataset to see the complete workflow.")
        if st.button("Open demo workspace", type="primary", width="stretch"):
            _load_demo()
            st.rerun()
    with intro_columns[1]:
        st.markdown("#### Supported sources")
        st.caption("CSV and XLSX tables, plus local SQLite and DuckDB database files.")
        st.caption(f"Maximum upload size: {_settings().max_upload_bytes / 1_000_000:.0f} MB per file.")
    st.divider()
    st.markdown("### Connect your own data")
    _load_inputs(workspace)
    if st.session_state.get("is_demo"):
        st.success("Demo data is ready. Move to Explore tables or Analyze.")
    elif workspace.tables:
        st.success(f"Loaded {len(workspace.tables)} table(s). Move to Explore tables or Analyze.")
    else:
        st.info("Use Load demo data in the sidebar, or upload CSV, Excel, SQLite, or DuckDB files.")


def _render_explore_page(workspace: DataWorkspace) -> None:
    st.markdown('<div class="page-kicker">Step 2 · Explore</div>', unsafe_allow_html=True)
    st.title("Explore the loaded tables")
    selected_table = st.selectbox("Choose a table", workspace.tables, key="explore_table")
    preview_rows = _settings().max_preview_rows
    total_rows = workspace.row_count(selected_table)
    frame = workspace.frame(selected_table, limit=preview_rows)
    columns = workspace.columns(selected_table)
    metrics = st.columns(3)
    metrics[0].metric("Rows", f"{total_rows:,}")
    metrics[1].metric("Columns", len(columns))
    metrics[2].metric("Missing values", workspace.missing_value_count(selected_table))
    if total_rows > preview_rows:
        st.caption(f"Showing the first {preview_rows:,} of {total_rows:,} rows.")
    st.markdown('<div class="preview-shell">', unsafe_allow_html=True)
    st.dataframe(frame, width="stretch", hide_index=True)
    st.markdown("</div>", unsafe_allow_html=True)
    with st.expander("Column details"):
        st.dataframe(pd.DataFrame(columns), width="stretch", hide_index=True)


def _render_visualization(frame: pd.DataFrame, key_prefix: str = "current") -> None:
    if frame is None or frame.empty or len(frame.columns) < 2:
        st.info("Return at least two columns to build a visualization.")
        return
    st.markdown("#### Build a visualization")
    columns = list(frame.columns)
    numeric_columns = [column for column in columns if pd.api.types.is_numeric_dtype(frame[column])]
    chart_type = st.selectbox("Chart type", ["Bar", "Line", "Scatter"], key=f"{key_prefix}_result_chart_type")
    controls = st.columns(2)
    x_column = controls[0].selectbox("X axis", columns, key=f"{key_prefix}_result_chart_x")
    y_options = [column for column in columns if column != x_column]
    default_y = next((column for column in numeric_columns if column != x_column), y_options[0])
    y_column = controls[1].selectbox(
        "Y axis", y_options, index=y_options.index(default_y), key=f"{key_prefix}_result_chart_y"
    )
    figure = build_chart(frame, chart_type, x_column, y_column)
    if figure is None:
        st.warning("Choose two different columns for the X and Y axes.")
    else:
        st.plotly_chart(figure, width="stretch", key=f"{key_prefix}_custom_result_chart")


def _render_execution(execution, summary, key_prefix: str = "current") -> None:
    st.success(summary.answer)
    if summary.insights:
        st.subheader("Key insights")
        insight_columns = st.columns(min(len(summary.insights), 3))
        for index, insight in enumerate(summary.insights):
            insight_columns[index % len(insight_columns)].markdown(
                f'<div class="insight-card insight-{index % 4}">{html.escape(str(insight))}</div>',
                unsafe_allow_html=True,
            )
    if summary.caveats:
        st.caption("Caveats: " + " ".join(html.escape(str(item)) for item in summary.caveats))
    metadata_columns = st.columns(4)
    metadata_columns[0].metric("Analysis mode", execution.mode.upper())
    metadata_columns[1].metric("Rows returned", f"{execution.row_count:,}")
    metadata_columns[2].metric("Execution", f"{execution.duration_ms:.0f} ms")
    validation_label = "Truncated" if execution.truncated else execution.validation_status
    metadata_columns[3].metric("Validation", validation_label)
    table_tab, chart_tab, code_tab = st.tabs(["Result table", "Visualization", "Generated code"])
    with table_tab:
        st.dataframe(execution.rows, width="stretch", hide_index=True)
        if execution.truncated:
            st.caption(f"Result limited to {execution.row_count:,} rows.")
    with chart_tab:
        _render_visualization(execution.rows, key_prefix=key_prefix)
        with st.expander("Automatic chart"):
            figure = auto_chart(execution.rows)
            if figure is not None:
                st.plotly_chart(figure, width="stretch", key=f"{key_prefix}_automatic_result_chart")
    with code_tab:
        st.code(execution.code, language=execution.mode)
        st.download_button(
            "Download generated code",
            data=execution.code,
            file_name=f"analysis.{ 'py' if execution.mode == 'python' else 'sql' }",
            mime="text/x-python" if execution.mode == "python" else "application/sql",
            width="stretch",
            key=f"{key_prefix}_download_code",
        )
    st.download_button(
        "Download result CSV",
        data=execution.rows.to_csv(index=False).encode("utf-8"),
        file_name="analysis-result.csv",
        mime="text/csv",
        key=f"{key_prefix}_download_csv",
    )


def main() -> None:
    _apply_styles()
    workspace = _workspace()
    _render_sidebar(workspace)

    if "source_label" not in st.session_state:
        st.session_state.source_label = "No data loaded"
    if "is_demo" not in st.session_state:
        st.session_state.is_demo = False
    if "current_page" not in st.session_state:
        st.session_state.current_page = "Load data"

    current_page = st.session_state.get("current_page", "Load data")
    if not workspace.tables:
        _render_data_page(workspace)
        return

    if current_page == "Load data":
        _render_data_page(workspace)
        return
    if current_page == "Explore tables":
        _render_explore_page(workspace)
        return

    _render_header(workspace)
    selected_question = _render_demo_questions()
    _render_history()
    question = (
        st.chat_input("Ask a question about your data")
        or st.session_state.pop("selected_question", None)
        or selected_question
    )
    if not question:
        return

    history = list(st.session_state.get("chat_history", []))
    st.session_state.chat_history.append({"role": "user", "content": question})
    with st.chat_message("user"):
        st.markdown(question)

    service = _analysis_service(workspace)
    try:
        with st.chat_message("assistant"):
            with st.spinner("Planning and executing analysis..."):
                execution, summary = service.analyze(question, history=history)
            _render_execution(execution, summary, key_prefix="live")
        st.session_state.chat_history.append({
            "role": "assistant",
            "content": summary.answer,
            "execution": execution,
            "summary": summary,
        })
    except Exception as exc:
        st.error("The analysis could not be completed.")
        with st.expander("Technical details"):
            st.code(str(exc))


if __name__ == "__main__":
    main()
