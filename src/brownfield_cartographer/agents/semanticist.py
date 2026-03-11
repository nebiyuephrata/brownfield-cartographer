from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List

from ..graph.knowledge_graph import KnowledgeGraph


@dataclass
class NodeSummary:
    """Lightweight container for semantic summaries."""

    id: str
    kind: str
    summary: str


class SemanticistAgent:
    """
    Semantic analysis agent.

    This implementation is intentionally LLM-agnostic. It produces simple,
    structured summaries from the existing graphs and stores them in the
    node metadata under a `semantic_summary` key so that an external LLM
    client can later refine or replace them.
    """

    def summarize_modules(self, kg: KnowledgeGraph) -> Dict[str, NodeSummary]:
        summaries: Dict[str, NodeSummary] = {}
        g = kg.module_graph

        for node_id, attrs in g.nodes(data=True):
            imports: List[str] = attrs.get("imports", [])
            functions: List[str] = attrs.get("functions", [])
            classes: List[str] = attrs.get("classes", [])

            text = (
                f"Module `{node_id}` defines "
                f"{len(functions)} functions and {len(classes)} classes, "
                f"and imports {len(imports)} modules."
            )

            summaries[node_id] = NodeSummary(id=node_id, kind="module", summary=text)

            metadata = attrs.get("metadata") or {}
            metadata["semantic_summary"] = text
            g.nodes[node_id]["metadata"] = metadata

        return summaries

    def summarize_datasets(self, kg: KnowledgeGraph) -> Dict[str, NodeSummary]:
        summaries: Dict[str, NodeSummary] = {}
        g = kg.lineage_graph

        for node_id, attrs in g.nodes(data=True):
            node_type = attrs.get("type", "unknown")

            upstream = list(g.predecessors(node_id))
            downstream = list(g.successors(node_id))

            text = (
                f"Dataset `{attrs.get('name', node_id)}` "
                f"(type={node_type}) has {len(upstream)} upstream "
                f"and {len(downstream)} downstream dependencies."
            )

            summaries[node_id] = NodeSummary(id=node_id, kind="dataset", summary=text)

            metadata = attrs.get("metadata") or {}
            metadata["semantic_summary"] = text
            g.nodes[node_id]["metadata"] = metadata

        return summaries

    def run(self, kg: KnowledgeGraph) -> Dict[str, Dict[str, NodeSummary]]:
        """
        Populate basic semantic summaries on module and dataset nodes.
        """
        module_summaries = self.summarize_modules(kg)
        dataset_summaries = self.summarize_datasets(kg)
        return {
            "modules": module_summaries,
            "datasets": dataset_summaries,
        }

