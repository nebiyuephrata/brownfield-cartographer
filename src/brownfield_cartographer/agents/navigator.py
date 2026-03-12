from __future__ import annotations

from dataclasses import dataclass
from typing import Iterable, List, Set

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

    # Multi-hop helpers

    def all_upstream_datasets(self, dataset_id: str) -> List[str]:
        g = self.kg.lineage_graph
        if dataset_id not in g:
            return []
        ancestors: Set[str] = set()
        frontier: List[str] = [dataset_id]
        while frontier:
            current = frontier.pop()
            for parent in g.predecessors(current):
                if parent not in ancestors:
                    ancestors.add(parent)
                    frontier.append(parent)
        return sorted(ancestors)

    def all_downstream_datasets(self, dataset_id: str) -> List[str]:
        g = self.kg.lineage_graph
        if dataset_id not in g:
            return []
        descendants: Set[str] = set()
        frontier: List[str] = [dataset_id]
        while frontier:
            current = frontier.pop()
            for child in g.successors(current):
                if child not in descendants:
                    descendants.add(child)
                    frontier.append(child)
        return sorted(descendants)

    def mart_downstream_datasets(self, dataset_id: str) -> List[str]:
        """
        Return all downstream datasets that are materialized as marts.
        """
        ids = self.all_downstream_datasets(dataset_id)
        g = self.kg.lineage_graph
        return sorted(
            [nid for nid in ids if g.nodes[nid].get("type") == "mart"]
        )

