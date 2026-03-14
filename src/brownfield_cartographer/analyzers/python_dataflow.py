from __future__ import annotations

import ast
from pathlib import Path
from typing import Dict, List, Optional, Tuple

from ..models.nodes import DatasetNode, Evidence
from ..models.edges import LineageEdge


READ_FUNCS = {
    # pandas
    ("pandas", "read_csv"): "read_csv",
    ("pandas", "read_parquet"): "read_parquet",
    ("pandas", "read_json"): "read_json",
    ("pandas", "read_excel"): "read_excel",
    ("pd", "read_csv"): "read_csv",
    ("pd", "read_parquet"): "read_parquet",
    ("pd", "read_json"): "read_json",
    ("pd", "read_excel"): "read_excel",
    # pandas SQL helpers
    ("pandas", "read_sql"): "read_sql",
    ("pd", "read_sql"): "read_sql",
}

WRITE_METHODS = {
    # pandas DataFrame.to_*
    "to_csv": "to_csv",
    "to_parquet": "to_parquet",
    "to_json": "to_json",
    "to_excel": "to_excel",
    # pandas SQL helper
    "to_sql": "to_sql",
}

PYSPARK_READS = {
    # spark.read.format(...).load(...) or spark.read.csv/parquet/json
    "csv": "spark_read_csv",
    "parquet": "spark_read_parquet",
    "json": "spark_read_json",
}

PYSPARK_WRITES = {
    # df.write.csv/parquet/json/save
    "csv": "spark_write_csv",
    "parquet": "spark_write_parquet",
    "json": "spark_write_json",
    "save": "spark_write_save",
}


def _get_full_attr_name(node: ast.AST) -> Optional[str]:
    """
    Return dotted name for an attribute or name node, e.g., pandas.read_csv, spark.read.csv.
    """
    parts: List[str] = []
    cur = node
    while isinstance(cur, ast.Attribute):
        parts.append(cur.attr)
        cur = cur.value
    if isinstance(cur, ast.Name):
        parts.append(cur.id)
    else:
        return None
    return ".".join(reversed(parts))


def _literal_str(arg: ast.AST) -> Optional[str]:
    if isinstance(arg, ast.Constant) and isinstance(arg.value, str):
        return arg.value
    return None


def _file_dataset_id(path_str: str) -> Tuple[str, str]:
    # Represent file datasets with a dedicated prefix
    return f"file:{path_str}", path_str.split("/")[-1]


def _table_dataset_id(name: str) -> Tuple[str, str]:
    return f"table:{name}", name


def extract_lineage_from_python(path: Path) -> Tuple[List[DatasetNode], List[LineageEdge]]:
    """
    Static Python dataflow detector for common IO patterns in pandas, PySpark, and SQLAlchemy.

    Produces a downstream dataset for the Python module (model:<module_name>) and edges:
      - read edges: source -> downstream
      - write edges: downstream -> target

    Edge metadata includes transformation_type, source_file, and operation. Evidence captures line ranges.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
    except FileNotFoundError:
        return [], []

    try:
        tree = ast.parse(text)
    except Exception:
        # If unparsable, skip gracefully
        return [], []

    evidence_file = Evidence(
        file_path=str(path),
        line_start=1,
        line_end=max(1, text.count("\n") + 1),
        method="python_ast",
    )

    module_name = path.stem
    downstream_id = f"model:{module_name}"
    downstream_node = DatasetNode(
        id=downstream_id,
        name=module_name,
        type="unknown",
        evidence=[evidence_file],
        metadata={"file_path": str(path)},
    )

    nodes: Dict[str, DatasetNode] = {downstream_id: downstream_node}
    edges: List[LineageEdge] = []

    # Track aliases from imports: import pandas as pd, from pandas import read_csv (less common for IO)
    alias_map: Dict[str, str] = {}

    class ImportVisitor(ast.NodeVisitor):
        def visit_Import(self, node: ast.Import) -> None:  # type: ignore[override]
            for alias in node.names:
                if alias.asname:
                    alias_map[alias.asname] = alias.name
                else:
                    alias_map[alias.name.split(".")[0]] = alias.name

        def visit_ImportFrom(self, node: ast.ImportFrom) -> None:  # type: ignore[override]
            # Track 'from pandas import read_csv' as alias to pandas.read_csv
            if node.module:
                for alias in node.names:
                    base = node.module.split(".")[0]
                    name = alias.asname or alias.name
                    alias_map[name] = f"{base}.{alias.name}"

    ImportVisitor().visit(tree)

    def resolve_prefix(name: str) -> str:
        # Map alias like 'pd' -> 'pandas' where possible
        root = name.split(".")[0]
        mapped = alias_map.get(root, root)
        if mapped != root:
            return mapped + name[len(root):]
        return name

    def ensure_node(node_id: str, name: str) -> None:
        if node_id not in nodes:
            nodes[node_id] = DatasetNode(
                id=node_id,
                name=name,
                type="unknown",
                evidence=[evidence_file],
                metadata={"file_path": str(path)},
            )

    class IOVisitor(ast.NodeVisitor):
        def visit_Call(self, node: ast.Call) -> None:  # type: ignore[override]
            func_name = _get_full_attr_name(node.func)
            if func_name:
                func_name = resolve_prefix(func_name)

            # pandas reads: pandas.read_csv(...)
            if func_name:
                for (lib, fn), op in READ_FUNCS.items():
                    if func_name == f"{lib}.{fn}":
                        arg0 = node.args[0] if node.args else None
                        path_str = _literal_str(arg0) if arg0 else None
                        ds_id, ds_name = _file_dataset_id(path_str) if path_str else (f"external:{op}", op)
                        ensure_node(ds_id, ds_name)
                        line_start = getattr(node, "lineno", 1)
                        line_end = getattr(node, "end_lineno", line_start)
                        edges.append(
                            LineageEdge(
                                id=f"{ds_id}->{downstream_id}#{line_start}",
                                source_dataset_id=ds_id,
                                target_dataset_id=downstream_id,
                                transformation_id=None,
                                evidence=[
                                    Evidence(
                                        file_path=str(path),
                                        line_start=line_start,
                                        line_end=line_end,
                                        method="python_ast",
                                        metadata={"call": func_name},
                                    )
                                ],
                                metadata={
                                    "operation": "read",
                                    "transformation_type": op,
                                    "source_file": str(path),
                                    "unresolved": path_str is None,
                                },
                            )
                        )
                        return

            # pandas writes: df.to_csv(...)
            if isinstance(node.func, ast.Attribute) and node.func.attr in WRITE_METHODS:
                op = WRITE_METHODS[node.func.attr]
                arg0 = node.args[0] if node.args else None
                path_str = _literal_str(arg0) if arg0 else None
                ds_id, ds_name = _file_dataset_id(path_str) if path_str else (f"external:{op}", op)
                ensure_node(ds_id, ds_name)
                line_start = getattr(node, "lineno", 1)
                line_end = getattr(node, "end_lineno", line_start)
                edges.append(
                    LineageEdge(
                        id=f"{downstream_id}->{ds_id}#{line_start}",
                        source_dataset_id=downstream_id,
                        target_dataset_id=ds_id,
                        transformation_id=None,
                        evidence=[
                            Evidence(
                                file_path=str(path),
                                line_start=line_start,
                                line_end=line_end,
                                method="python_ast",
                                metadata={"call": op},
                            )
                        ],
                        metadata={
                            "operation": "write",
                            "transformation_type": op,
                            "source_file": str(path),
                            "unresolved": path_str is None,
                        },
                    )
                )
                return

            # pandas SQL helpers: pandas.read_sql(sql, con) and DataFrame.to_sql(name, con, ...)
            if func_name in ("pandas.read_sql", "pd.read_sql"):
                # First arg can be a table name or a SQL query string
                arg0 = node.args[0] if node.args else None
                name_or_sql = _literal_str(arg0) if arg0 else None
                if name_or_sql:
                    if " " in name_or_sql.lower():
                        ds_id, ds_name = (f"query:{hash(name_or_sql)}", "sql_query")
                    else:
                        ds_id, ds_name = _table_dataset_id(name_or_sql)
                else:
                    ds_id, ds_name = ("external:read_sql", "read_sql")
                ensure_node(ds_id, ds_name)
                line_start = getattr(node, "lineno", 1)
                line_end = getattr(node, "end_lineno", line_start)
                edges.append(
                    LineageEdge(
                        id=f"{ds_id}->{downstream_id}#{line_start}",
                        source_dataset_id=ds_id,
                        target_dataset_id=downstream_id,
                        transformation_id=None,
                        evidence=[
                            Evidence(
                                file_path=str(path),
                                line_start=line_start,
                                line_end=line_end,
                                method="python_ast",
                                metadata={"call": "read_sql"},
                            )
                        ],
                        metadata={
                            "operation": "read",
                            "transformation_type": "read_sql",
                            "source_file": str(path),
                            "unresolved": name_or_sql is None,
                        },
                    )
                )
                return

            if isinstance(node.func, ast.Attribute) and node.func.attr == "to_sql":
                # First arg is table name
                arg0 = node.args[0] if node.args else None
                table_name = _literal_str(arg0) if arg0 else None
                ds_id, ds_name = _table_dataset_id(table_name) if table_name else ("external:to_sql", "to_sql")
                ensure_node(ds_id, ds_name)
                line_start = getattr(node, "lineno", 1)
                line_end = getattr(node, "end_lineno", line_start)
                edges.append(
                    LineageEdge(
                        id=f"{downstream_id}->{ds_id}#{line_start}",
                        source_dataset_id=downstream_id,
                        target_dataset_id=ds_id,
                        transformation_id=None,
                        evidence=[
                            Evidence(
                                file_path=str(path),
                                line_start=line_start,
                                line_end=line_end,
                                method="python_ast",
                                metadata={"call": "to_sql"},
                            )
                        ],
                        metadata={
                            "operation": "write",
                            "transformation_type": "to_sql",
                            "source_file": str(path),
                            "unresolved": table_name is None,
                        },
                    )
                )
                return

            # PySpark: spark.read.csv/parquet/json and df.write.csv/parquet/json/save
            if func_name and func_name.startswith("spark.read."):
                fmt = func_name.split(".")[-1]
                op = PYSPARK_READS.get(fmt)
                if op:
                    arg0 = node.args[0] if node.args else None
                    path_str = _literal_str(arg0) if arg0 else None
                    ds_id, ds_name = _file_dataset_id(path_str) if path_str else (f"external:{op}", op)
                    ensure_node(ds_id, ds_name)
                    line_start = getattr(node, "lineno", 1)
                    line_end = getattr(node, "end_lineno", line_start)
                    edges.append(
                        LineageEdge(
                            id=f"{ds_id}->{downstream_id}#{line_start}",
                            source_dataset_id=ds_id,
                            target_dataset_id=downstream_id,
                            transformation_id=None,
                            evidence=[
                                Evidence(
                                    file_path=str(path),
                                    line_start=line_start,
                                    line_end=line_end,
                                    method="python_ast",
                                    metadata={"call": func_name},
                                )
                            ],
                            metadata={
                                "operation": "read",
                                "transformation_type": op,
                                "source_file": str(path),
                                "unresolved": path_str is None,
                            },
                        )
                    )
                    return

            if func_name and func_name.endswith(".write.save"):
                op = PYSPARK_WRITES.get("save")
                arg0 = node.args[0] if node.args else None
                path_str = _literal_str(arg0) if arg0 else None
                ds_id, ds_name = _file_dataset_id(path_str) if path_str else (f"external:{op}", op)
                ensure_node(ds_id, ds_name)
                line_start = getattr(node, "lineno", 1)
                line_end = getattr(node, "end_lineno", line_start)
                edges.append(
                    LineageEdge(
                        id=f"{downstream_id}->{ds_id}#{line_start}",
                        source_dataset_id=downstream_id,
                        target_dataset_id=ds_id,
                        transformation_id=None,
                        evidence=[
                            Evidence(
                                file_path=str(path),
                                line_start=line_start,
                                line_end=line_end,
                                method="python_ast",
                                metadata={"call": func_name},
                            )
                        ],
                        metadata={
                            "operation": "write",
                            "transformation_type": op,
                            "source_file": str(path),
                            "unresolved": path_str is None,
                        },
                    )
                )
                return

            if func_name and ".write." in func_name:
                fmt = func_name.split(".")[-1]
                op = PYSPARK_WRITES.get(fmt)
                if op:
                    arg0 = node.args[0] if node.args else None
                    path_str = _literal_str(arg0) if arg0 else None
                    ds_id, ds_name = _file_dataset_id(path_str) if path_str else (f"external:{op}", op)
                    ensure_node(ds_id, ds_name)
                    line_start = getattr(node, "lineno", 1)
                    line_end = getattr(node, "end_lineno", line_start)
                    edges.append(
                        LineageEdge(
                            id=f"{downstream_id}->{ds_id}#{line_start}",
                            source_dataset_id=downstream_id,
                            target_dataset_id=ds_id,
                            transformation_id=None,
                            evidence=[
                                Evidence(
                                    file_path=str(path),
                                    line_start=line_start,
                                    line_end=line_end,
                                    method="python_ast",
                                    metadata={"call": func_name},
                                )
                            ],
                            metadata={
                                "operation": "write",
                                "transformation_type": op,
                                "source_file": str(path),
                                "unresolved": path_str is None,
                            },
                        )
                    )
                    return

            self.generic_visit(node)

    IOVisitor().visit(tree)

    return list(nodes.values()), edges
