from __future__ import annotations

from pathlib import Path
from typing import List, Tuple
import logging
import re

try:
    import sqlglot
    from sqlglot import exp
except Exception:  # pragma: no cover
    sqlglot = None
    exp = None

from ..models.edges import LineageEdge
from ..models.nodes import DatasetNode, Evidence


logger = logging.getLogger(__name__)


_JINJA_BLOCK_RE = re.compile(r"\{%-?[\s\S]*?-?%\}")
_JINJA_COMMENT_RE = re.compile(r"\{#[\s\S]*?#\}")
_JINJA_REF_RE = re.compile(r"\{\{\s*ref\(\s*['\"]([^'\"]+)['\"]\s*\)\s*\}\}")
_JINJA_SOURCE_RE = re.compile(
    r"\{\{\s*source\(\s*['\"]([^'\"]+)['\"]\s*,\s*['\"]([^'\"]+)['\"]\s*\)\s*\}\}"
)
_JINJA_EXPR_RE = re.compile(r"\{\{[\s\S]*?\}\}")


def _strip_jinja(sql_text: str) -> str:
    """
    Remove or simplify dbt/Jinja templating so sqlglot can parse.
    - strips {% ... %} blocks and {# ... #} comments
    - replaces {{ ref('model') }} with model
    - replaces {{ source('schema','table') }} with schema.table
    """
    text = _JINJA_BLOCK_RE.sub(" ", sql_text)
    text = _JINJA_COMMENT_RE.sub(" ", text)
    text = _JINJA_REF_RE.sub(r"\1", text)
    text = _JINJA_SOURCE_RE.sub(r"\1.\2", text)
    # Replace any remaining Jinja expressions with a neutral token.
    text = _JINJA_EXPR_RE.sub("jinja_var", text)
    return text


def _parse_statements(sql_text: str):
    """
    Try parsing the SQL text across a few common dialects.
    Returns None if unparseable (caller should log and skip gracefully).
    """
    if sqlglot is None:
        return [sql_text]
    dialects: List[str | None] = [None, "ansi", "snowflake", "bigquery"]
    last_error: Exception | None = None
    for dialect in dialects:
        try:
            if dialect is None:
                return list(sqlglot.parse(sql_text))
            return list(sqlglot.parse(sql_text, read=dialect))
        except Exception as exc:
            last_error = exc
            continue
    logger.warning("Unparseable SQL; skipping lineage extraction: %s", last_error)
    return None


def _extract_dbt_refs(sql_text: str) -> List[str]:
    """
    Very small helper to extract dbt ref() targets without requiring Jinja rendering.
    """
    pattern = r"ref\(['\"]([^'\"]+)['\"]\)"
    return re.findall(pattern, sql_text)


def extract_lineage_from_sql(path: Path) -> Tuple[List[DatasetNode], List[LineageEdge]]:
    """
    Very small sqlglot-based lineage extractor.

    For now we:
    - Treat the file stem as the downstream dataset.
    - Collect all table references as upstream datasets.
    - Attach simple lineage statistics into DatasetNode.metadata.
    """
    sql_text = path.read_text(encoding="utf-8", errors="ignore")
    sql_text = _strip_jinja(sql_text)
    evidence = Evidence(
        file_path=str(path),
        line_start=1,
        line_end=max(1, sql_text.count("\n") + 1),
        method="sqlglot",
    )

    statements = _parse_statements(sql_text)
    if statements is None:
        return [], []

    downstream_name = path.stem
    downstream_id = f"model:{downstream_name}"

    # Compute simple stats: total number of statements and tables referenced.
    all_tables: List[str] = []
    write_targets: List[str] = []
    if sqlglot is None:
        refs = re.findall(r"(?:from|join)\s+([a-zA-Z_][\w.]*)", sql_text, flags=re.IGNORECASE)
        all_tables.extend(refs)
        # Best-effort write target detection so migrations/DDL still produce lineage.
        write_targets.extend(
            re.findall(
                r"(?:create\s+table\s+(?:if\s+not\s+exists\s+)?|insert\s+into\s+|merge\s+into\s+|update\s+|delete\s+from\s+)([a-zA-Z_][\w.]*)",
                sql_text,
                flags=re.IGNORECASE,
            )
        )
    else:
        for stmt in statements:
            # Track read tables from FROM/JOIN/CTEs/subqueries via Table nodes.
            for table in stmt.find_all(exp.Table):
                if table.name:
                    all_tables.append(table.name)

            # Track simple write targets for INSERT/CREATE TABLE AS / MERGE.
            if isinstance(stmt, (exp.Insert, exp.Update, exp.Merge, exp.Delete, exp.Create)):
                target = getattr(stmt, "this", None)
                if isinstance(target, exp.Table) and target.name:
                    write_targets.append(target.name)

    dataset_nodes = {}

    downstream_node = DatasetNode(
        id=downstream_id,
        name=downstream_name,
        type="unknown",
        evidence=[evidence],
        metadata={
            "source_table_count": len(set(all_tables)),
            "statement_count": len(statements),
            "file_path": str(path),
        },
    )
    dataset_nodes[downstream_id] = downstream_node

    lineage_edges: List[LineageEdge] = []

    # Upstream read tables feeding the downstream model.
    for table_name in sorted(set(all_tables)):
        upstream_id = f"table:{table_name}"
        if upstream_id not in dataset_nodes:
            dataset_nodes[upstream_id] = DatasetNode(
                id=upstream_id,
                name=table_name,
                type="unknown",
                evidence=[evidence],
                metadata={"file_path": str(path)},
            )

        edge_id = f"{upstream_id}->{downstream_id}"
        lineage_edges.append(
            LineageEdge(
                id=edge_id,
                source_dataset_id=upstream_id,
                target_dataset_id=downstream_id,
                transformation_id=None,
                evidence=[evidence],
                metadata={"operation": "read"},
            )
        )

    # dbt ref() targets are treated as additional upstream model dependencies.
    for ref_name in sorted(set(_extract_dbt_refs(sql_text))):
        ref_id = f"model:{ref_name}"
        if ref_id not in dataset_nodes:
            dataset_nodes[ref_id] = DatasetNode(
                id=ref_id,
                name=ref_name,
                type="unknown",
                evidence=[evidence],
                metadata={"file_path": str(path), "via": "dbt_ref"},
            )
        edge_id = f"{ref_id}->{downstream_id}"
        lineage_edges.append(
            LineageEdge(
                id=edge_id,
                source_dataset_id=ref_id,
                target_dataset_id=downstream_id,
                transformation_id=None,
                evidence=[evidence],
                metadata={"operation": "read", "via": "dbt_ref"},
            )
        )

    # For write operations, attach edges from downstream model to physical tables.
    for target_name in sorted(set(write_targets)):
        target_id = f"table:{target_name}"
        if target_id not in dataset_nodes:
            dataset_nodes[target_id] = DatasetNode(
                id=target_id,
                name=target_name,
                type="mart",
                evidence=[evidence],
                metadata={"file_path": str(path), "operation": "write"},
            )
        edge_id = f"{downstream_id}->{target_id}"
        lineage_edges.append(
            LineageEdge(
                id=edge_id,
                source_dataset_id=downstream_id,
                target_dataset_id=target_id,
                transformation_id=None,
                evidence=[evidence],
                metadata={"operation": "write"},
            )
        )

    return list(dataset_nodes.values()), lineage_edges
