from __future__ import annotations

from pathlib import Path
from typing import List, Tuple

import sqlglot
from sqlglot import exp

from ..models.edges import LineageEdge
from ..models.nodes import DatasetNode, Evidence, TransformationNode


def extract_lineage_from_sql(path: Path) -> Tuple[List[DatasetNode], List[LineageEdge]]:
    """
    Very small sqlglot-based lineage extractor.

    For now we:
    - Treat the file stem as the downstream dataset.
    - Collect all table references as upstream datasets.
    """
    sql_text = path.read_text(encoding="utf-8", errors="ignore")
    evidence = Evidence(
        file_path=str(path),
        line_start=1,
        line_end=max(1, sql_text.count("\n") + 1),
        method="sqlglot",
    )

    try:
        statements = list(sqlglot.parse(sql_text))
    except sqlglot.errors.ParseError:
        return [], []

    downstream_name = path.stem
    downstream_id = f"model:{downstream_name}"
    downstream_node = DatasetNode(
        id=downstream_id,
        name=downstream_name,
        type="unknown",
        evidence=[evidence],
    )

    upstream_ids: List[str] = []

    for stmt in statements:
        for table in stmt.find_all(exp.Table):
            table_name = table.name
            if not table_name:
                continue
            upstream_id = f"table:{table_name}"
            upstream_ids.append(upstream_id)

    dataset_nodes = {downstream_id: downstream_node}
    lineage_edges: List[LineageEdge] = []

    for uid in sorted(set(upstream_ids)):
        if uid not in dataset_nodes:
            dataset_nodes[uid] = DatasetNode(
                id=uid,
                name=uid.split(":", 1)[1],
                type="unknown",
                evidence=[evidence],
            )

        edge_id = f"{uid}->{downstream_id}"
        lineage_edges.append(
            LineageEdge(
                id=edge_id,
                source_dataset_id=uid,
                target_dataset_id=downstream_id,
                transformation_id=None,
                evidence=[evidence],
            )
        )

    return list(dataset_nodes.values()), lineage_edges

