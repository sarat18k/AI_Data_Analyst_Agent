import pandas as pd
import plotly.express as px


def _date_like(series: pd.Series) -> bool:
    if pd.api.types.is_numeric_dtype(series):
        return False
    parsed = pd.to_datetime(series, errors="coerce", format="mixed")
    return parsed.notna().sum() > 0 and parsed.notna().mean() >= 0.8


def _id_like(column: str) -> bool:
    name = str(column).lower().replace("-", "_").replace(" ", "_")
    return name == "id" or name.endswith("_id") or name.startswith("id_")


def _chart_title(kind: str, x_column: str, y_column: str) -> str:
    if kind == "line":
        return f"{y_column} over time"
    if kind == "bar":
        return f"{y_column} by {x_column}"
    return f"{y_column} vs {x_column}"


def build_chart(frame: pd.DataFrame, chart_type: str, x_column: str, y_column: str):
    """Build a validated chart from explicit field selections."""
    if x_column == y_column or x_column not in frame.columns or y_column not in frame.columns:
        return None
    chart_frame = frame.copy()
    if chart_type == "Line":
        chart_frame[x_column] = pd.to_datetime(chart_frame[x_column], format="mixed", errors="coerce")
        chart_frame = chart_frame.dropna(subset=[x_column]).sort_values(x_column)
        figure = px.line(
            chart_frame,
            x=x_column,
            y=y_column,
            markers=True,
            title=_chart_title("line", x_column, y_column),
        )
    elif chart_type == "Bar":
        chart_frame = chart_frame.sort_values(y_column, ascending=False)
        figure = px.bar(
            chart_frame,
            x=x_column,
            y=y_column,
            text_auto=True,
            title=_chart_title("bar", x_column, y_column),
        )
    else:
        figure = px.scatter(
            chart_frame,
            x=x_column,
            y=y_column,
            trendline="ols" if len(chart_frame) >= 3 else None,
            title=_chart_title("scatter", x_column, y_column),
        )
    return figure.update_layout(template="plotly_white", height=430)


def auto_chart(frame: pd.DataFrame):
    if frame is None or frame.empty or frame.shape == (1, 1):
        return None
    date_columns = [column for column in frame.columns if _date_like(frame[column])]
    numeric_columns = [column for column in frame.columns if pd.api.types.is_numeric_dtype(frame[column])]
    measure_columns = [column for column in numeric_columns if not _id_like(column)] or numeric_columns
    if date_columns and numeric_columns:
        date_column = date_columns[0]
        measure_column = measure_columns[0]
        chart_frame = frame.copy()
        chart_frame[date_column] = pd.to_datetime(chart_frame[date_column], format="mixed", errors="coerce")
        chart_frame = chart_frame.sort_values(date_column)
        figure = px.line(
            chart_frame,
            x=date_column,
            y=measure_column,
            markers=True,
            title=_chart_title("line", date_column, measure_column),
        )
        return figure.update_layout(template="plotly_white", height=430)
    text_columns = [
        column for column in frame.columns
        if not pd.api.types.is_numeric_dtype(frame[column]) and column not in date_columns
    ]
    if text_columns and measure_columns and len(frame) <= 50:
        category_column = text_columns[0]
        measure_column = measure_columns[0]
        chart_frame = frame.sort_values(measure_column, ascending=False)
        figure = px.bar(
            chart_frame,
            x=category_column,
            y=measure_column,
            text_auto=True,
            title=_chart_title("bar", category_column, measure_column),
        )
        return figure.update_layout(template="plotly_white", height=430)
    distinct_measures = measure_columns if len(measure_columns) >= 2 else numeric_columns
    if len(distinct_measures) >= 2:
        x_column, y_column = distinct_measures[:2]
        figure = px.scatter(
            frame,
            x=x_column,
            y=y_column,
            trendline="ols" if len(frame) >= 3 else None,
            title=_chart_title("scatter", x_column, y_column),
        )
        return figure.update_layout(template="plotly_white", height=430)
    return None
