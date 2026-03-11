from __future__ import annotations

from dataclasses import dataclass
from typing import List

from ..graph.knowledge_graph import KnowledgeGraph


@dataclass
class NavigationResult:
    target: str
    upstream: List[str]
    downstream: List[str]


class NavigatorAgent:
    """
    Query/navigation agent over the knowledge graph.

    This is intentionally CLI/backend-focused; any interactive UI can call
    these helpers to inspect upstream/downstream neighborhoods of nodes.
    """

    def __init__(self, kg: KnowledgeGraph) -> None:
        self.kg = kg

    def inspect_dataset(self, dataset_id: str) -> NavigationResult:
        g = self.kg.lineage_graph
        upstream = list(g.predecessors(dataset_id)) if dataset_id in g else []
        downstream = list(g.successors(dataset_id)) if dataset_id in g else []
        return NavigationResult(target=dataset_id, upstream=upstream, downstream=downstream)

    def inspect_module(self, module_id: str) -> NavigationResult:
        g = self.kg.module_graph
        upstream = list(g.predecessors(module_id)) if module_id in g else []
        downstream = list(g.successors(module_id)) if module_id in g else []
        return NavigationResult(target=module_id, upstream=upstream, downstream=downstream)

