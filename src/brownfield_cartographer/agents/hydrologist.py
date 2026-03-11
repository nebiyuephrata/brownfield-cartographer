from __future__ import annotations

from pathlib import Path

from ..analyzers.sql_lineage import extract_lineage_from_sql
from ..graph.knowledge_graph import KnowledgeGraph


class HydrologistAgent:
    """
    SQL/data lineage agent that constructs dataset-level lineage graph.
    """

    def run(self, repo_path: Path, kg: KnowledgeGraph) -> None:
        for path in repo_path.rglob("*.sql"):
            dataset_nodes, lineage_edges = extract_lineage_from_sql(path)
            for node in dataset_nodes:
                kg.add_dataset_node(node)
            for edge in lineage_edges:
                kg.add_lineage_edge(edge)

