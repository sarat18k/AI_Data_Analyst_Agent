import ast
import builtins

import pandas as pd

BLOCKED_NAMES = {
    "__import__", "breakpoint", "compile", "eval", "exec", "input", "open",
    "os", "pathlib", "shutil", "socket", "subprocess", "sys",
}
ALLOWED_BUILTINS = {"abs", "len", "max", "min", "round", "sorted", "sum"}


def validate_python(code: str) -> ast.AST:
    if not code or len(code) > 12_000:
        raise ValueError("Python analysis code is empty or too large.")
    try:
        tree = ast.parse(code, mode="exec")
    except SyntaxError as exc:
        raise ValueError(f"Invalid Python syntax: {exc.msg}.") from exc
    for node in ast.walk(tree):
        if isinstance(node, (ast.Import, ast.ImportFrom, ast.With, ast.AsyncWith, ast.Try, ast.Raise)):
            raise ValueError("Imports, context managers, exception handling, and raises are not allowed.")
        if isinstance(node, ast.Name) and node.id in BLOCKED_NAMES:
            raise ValueError(f"Python name is not allowed: {node.id}.")
        if isinstance(node, ast.Attribute) and node.attr.startswith("_"):
            raise ValueError("Private Python attributes are not allowed.")
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Attribute):
            if isinstance(node.func.value, ast.Name) and node.func.value.id == "pd":
                raise ValueError(
                    "Direct pandas module calls are not allowed; operate on supplied DataFrames."
                )
        if isinstance(node, ast.Call) and isinstance(node.func, ast.Name):
            if node.func.id not in ALLOWED_BUILTINS | {"DataFrame", "Series"}:
                raise ValueError(f"Python function is not allowed: {node.func.id}.")
    return tree


def execute_python(code: str, frames: dict[str, pd.DataFrame]) -> pd.DataFrame:
    tree = validate_python(code)
    namespace = {"pd": pd, "DataFrame": pd.DataFrame, "Series": pd.Series, **frames}
    namespace["__builtins__"] = {
        name: getattr(builtins, name) for name in ALLOWED_BUILTINS if hasattr(builtins, name)
    }
    exec(compile(tree, "<analysis>", "exec"), namespace, namespace)
    result = namespace.get("result")
    if result is None:
        raise ValueError("Python analysis must assign its final output to `result`.")
    if isinstance(result, pd.Series):
        return result.to_frame()
    if isinstance(result, pd.DataFrame):
        return result
    return pd.DataFrame({"result": [result]})
