from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, Iterable, List, Optional, Set

import networkx as nx

from ..models.edges import (
    DagDependencyEdge,
    LineageEdge,
    ModuleDependencyEdge,
    ModuleOwnershipEdge,
    SimilarityEdge,
)
from ..models.nodes import DagNode, DatasetNode, ModuleNode, TransformationNode


SCHEMA_VERSION = "1.0.0"


class KnowledgeGraph:
    """
    Wrapper around networkx graphs for modules and lineage.
    """

    def __init__(self) -> None:
        self.module_graph = nx.DiGraph()
        self.lineage_graph = nx.DiGraph()

    # Module graph operations

    def add_module_node(self, node: ModuleNode) -> None:
        self.module_graph.add_node(node.id, **node.model_dump())

    def add_module_edge(self, edge: ModuleDependencyEdge) -> None:
        self.module_graph.add_edge(edge.source_module_id, edge.target_module_id, **edge.model_dump())

    def add_module_ownership_edge(self, edge: ModuleOwnershipEdge) -> None:
        """
        Attach an ownership edge from a module to a dataset it manages.
        """
        self.module_graph.add_edge(edge.module_id, edge.dataset_id, **edge.model_dump())

    # Lineage graph operations

    def add_dataset_node(self, node: DatasetNode) -> None:
        self.lineage_graph.add_node(node.id, **node.model_dump())

    def add_transformation_node(self, node: TransformationNode) -> None:
        self.lineage_graph.add_node(node.id, **node.model_dump())

    def add_lineage_edge(self, edge: LineageEdge) -> None:
        self.lineage_graph.add_edge(edge.source_dataset_id, edge.target_dataset_id, **edge.model_dump())

    def add_dag_node(self, node: DagNode) -> None:
        """
        Store orchestration tasks in the lineage graph so that end-to-end
        data flow and scheduling dependencies share a common DAG.
        """
        self.lineage_graph.add_node(node.id, **node.model_dump())

    def add_dag_edge(self, edge: DagDependencyEdge) -> None:
        self.lineage_graph.add_edge(edge.upstream_task_id, edge.downstream_task_id, **edge.model_dump())

    def add_similarity_edge(self, edge: SimilarityEdge) -> None:
        """
        Store similarity relations in the module graph since they typically
        connect modules or other code artifacts.
        """
        self.module_graph.add_edge(edge.source_id, edge.target_id, **edge.model_dump())

    # Convenience queries

    def get_dataset_by_name(self, name: str) -> Optional[str]:
        """
        Return the first dataset node id whose `name` attribute matches the given name.
        """
        for node_id, attrs in self.lineage_graph.nodes(data=True):
            if attrs.get("name") == name:
                return node_id
        return None

    def neighbors_subgraph(self, node_id: str, graph: nx.DiGraph) -> nx.DiGraph:
        """
        Return a small subgraph containing a node and its immediate predecessors/successors.
        """
        if node_id not in graph:
            return nx.DiGraph()
        nodes: Set[str] = {node_id}
        nodes.update(graph.predecessors(node_id))
        nodes.update(graph.successors(node_id))
        return graph.subgraph(nodes).copy()

    # Persistence helpers

    def _graph_to_payload(self, graph: nx.DiGraph) -> Dict[str, Any]:
        nodes = []
        for node_id, attrs in graph.nodes(data=True):
            nodes.append({"id": node_id, **attrs})

        edges = []
        for source, target, attrs in graph.edges(data=True):
            edges.append({"source": source, "target": target, **attrs})

        return {
            "schema_version": SCHEMA_VERSION,
            "nodes": nodes,
            "edges": edges,
        }

    @staticmethod
    def _payload_to_graph(payload: Dict[str, Any]) -> nx.DiGraph:
        g = nx.DiGraph()
        for node in payload.get("nodes", []):
            node_id = node["id"]
            attrs = {k: v for k, v in node.items() if k != "id"}
            g.add_node(node_id, **attrs)
        for edge in payload.get("edges", []):
            source = edge["source"]
            target = edge["target"]
            attrs = {k: v for k, v in edge.items() if k not in ("source", "target")}
            g.add_edge(source, target, **attrs)
        return g

    def _validate_edges(self, graph: nx.DiGraph) -> List[str]:
        """
        Return a list of human-readable error strings for edges that reference missing nodes.
        """
        errors: List[str] = []
        for source, target in graph.edges():
            if source not in graph.nodes:
                errors.append(f"Edge from '{source}' to '{target}' has missing source node.")
            if target not in graph.nodes:
                errors.append(f"Edge from '{source}' to '{target}' has missing target node.")
        return errors

    def to_module_json(self) -> Dict[str, Any]:
        errors = self._validate_edges(self.module_graph)
        if errors:
            raise ValueError(f"Module graph has invalid edges: {errors}")
        return self._graph_to_payload(self.module_graph)

    def to_lineage_json(self) -> Dict[str, Any]:
        errors = self._validate_edges(self.lineage_graph)
        if errors:
            raise ValueError(f"Lineage graph has invalid edges: {errors}")
        return self._graph_to_payload(self.lineage_graph)

    def save_module_graph(self, path: Path) -> None:
        payload = self.to_module_json()
        path.write_text(_to_json(payload), encoding="utf-8")

    def save_lineage_graph(self, path: Path) -> None:
        payload = self.to_lineage_json()
        path.write_text(_to_json(payload), encoding="utf-8")

    @classmethod
    def load_from_paths(
        cls,
        module_graph_path: Path | None = None,
        lineage_graph_path: Path | None = None,
    ) -> "KnowledgeGraph":
        """
        Load module and/or lineage graphs from JSON payloads.
        """
        kg = cls()
        if module_graph_path and module_graph_path.exists():
            module_payload = _from_json(module_graph_path.read_text(encoding="utf-8"))
            kg.module_graph = cls._payload_to_graph(module_payload)
        if lineage_graph_path and lineage_graph_path.exists():
            lineage_payload = _from_json(
                lineage_graph_path.read_text(encoding="utf-8")
            )
            kg.lineage_graph = cls._payload_to_graph(lineage_payload)
        return kg


def _to_json(obj: Dict[str, Any]) -> str:
    import json

    return json.dumps(obj, indent=2, sort_keys=True)


def _from_json(text: str) -> Dict[str, Any]:
    import json

    return json.loads(text)

