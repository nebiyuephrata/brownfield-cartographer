from __future__ import annotations

import logging
from pathlib import Path
from typing import Dict, Iterable, List, Sequence, Set

import networkx as nx

logger = logging.getLogger(__name__)

from ..analyzers.sql_lineage import extract_lineage_from_sql
from ..analyzers.python_dataflow import extract_lineage_from_python
from ..analyzers.dag_config_parser import (
    extract_model_metadata,
    extract_source_definitions,
    parse_dbt_project_config,
)
from ..graph.knowledge_graph import KnowledgeGraph
from ..models.nodes import TransformationNode, DatasetNode


class HydrologistAgent:
    """
    SQL/data lineage agent that constructs dataset-level lineage graph and
    exposes helper queries for blast radius and dependency navigation.
    """

    def __init__(self, model_globs: Iterable[str] | None = None) -> None:
        # Default to dbt-style models directory, but still allow generic *.sql fallback.
        self.model_globs: List[str] = list(model_globs) if model_globs is not None else [
            "models/**/*.sql",
            "**/models/**/*.sql",
        ]

    def _iter_sql_files(self, repo_path: Path) -> Sequence[Path]:
        # First yield dbt-style model files if they exist, otherwise all *.sql.
        matched: List[Path] = []
        for pattern in self.model_globs:
            matched.extend(repo_path.rglob(pattern))
        if matched:
            return matched
        return list(repo_path.rglob("*.sql"))

    def _iter_python_files(self, repo_path: Path) -> Sequence[Path]:
        return [p for p in repo_path.rglob("**/*.py") if "__pycache__" not in str(p)]

    def _load_dbt_metadata(self, repo_path: Path) -> Dict[str, Dict]:
        """
        Load dbt-style model metadata from any YAML files under the repo.
        Returns a mapping of model name -> normalized metadata.
        """
        model_meta: Dict[str, Dict] = {}
        for yaml_path in repo_path.rglob("*.yml"):
            cfg = parse_dbt_project_config(yaml_path)
            if not cfg:
                continue
            for model in cfg.get("models", []) or []:
                name = model.get("name")
                if not name:
                    continue
                meta = extract_model_metadata(model)
                if meta:
                    # Last-writer wins if duplicates exist; good enough for now.
                    model_meta[name] = meta
        return model_meta

    def _enrich_with_sources(self, repo_path: Path, kg: KnowledgeGraph) -> None:
        """
        Enrich upstream tables in the lineage graph with dbt source definitions when present.
        """
        for yaml_path in repo_path.rglob("*.yml"):
            cfg = parse_dbt_project_config(yaml_path)
            if not cfg:
                continue
            sources = extract_source_definitions(cfg)
            for src in sources:
                table_name = src.get("table_name")
                if not table_name:
                    continue
                node_id = f"table:{table_name}"
                if node_id in kg.lineage_graph.nodes:
                    attrs = kg.lineage_graph.nodes[node_id]
                    metadata = attrs.get("metadata") or {}
                    source_list = metadata.get("sources") or []
                    source_list.append(src)
                    metadata["sources"] = source_list
                    kg.lineage_graph.nodes[node_id]["metadata"] = metadata

    def run(self, repo_path: Path, kg: KnowledgeGraph) -> None:
        model_metadata = self._load_dbt_metadata(repo_path)

        for path in self._iter_sql_files(repo_path):
            try:
                dataset_nodes, lineage_edges = extract_lineage_from_sql(path)
            except Exception as exc:
                logger.warning("Skipping SQL file %s: %s", path, exc)
                continue

            # Attach dbt model metadata when names match the downstream dataset.
            for node in dataset_nodes:
                if isinstance(node, DatasetNode):
                    meta = model_metadata.get(node.name)
                    if meta:
                        combined = dict(node.metadata)
                        combined.update(meta)
                        node.metadata = combined
                kg.add_dataset_node(node)

            # Create a TransformationNode for this SQL model and attach it to edges.
            if dataset_nodes:
                downstream = next((n for n in dataset_nodes if n.id.startswith("model:")), None)
            else:
                downstream = None

            transformation_id = None
            if downstream is not None:
                transformation_id = f"transformation:{downstream.name}"
                transform_node = TransformationNode(
                    id=transformation_id,
                    name=downstream.name,
                    evidence=downstream.evidence,
                )
                kg.add_transformation_node(transform_node)

            for edge in lineage_edges:
                if transformation_id is not None:
                    edge.transformation_id = transformation_id
                kg.add_lineage_edge(edge)

        # 2) Python dataflow lineage
        for py_path in self._iter_python_files(repo_path):
            try:
                dataset_nodes, lineage_edges = extract_lineage_from_python(py_path)
            except Exception as exc:
                logger.warning("Skipping PY file %s: %s", py_path, exc)
                continue

            for node in dataset_nodes:
                if isinstance(node, DatasetNode):
                    kg.add_dataset_node(node)
            for edge in lineage_edges:
                kg.add_lineage_edge(edge)

        # After all lineage extraction, enrich any upstream table nodes with source definitions.
        self._enrich_with_sources(repo_path, kg)

    # ---- Lineage query helpers ---------------------------------------------

    def blast_radius(self, kg: KnowledgeGraph, dataset_id: str) -> Set[str]:
        """
        Return all downstream datasets reachable from the given dataset_id.
        """
        g = kg.lineage_graph
        if dataset_id not in g:
            return set()
        return set(nx.descendants(g, dataset_id))

    def find_sources(self, kg: KnowledgeGraph, dataset_id: str) -> Set[str]:
        """
        Return all upstream source datasets (in_degree == 0) that can reach dataset_id.
        """
        g = kg.lineage_graph
        if dataset_id not in g:
            return set()
        upstream: Set[str] = set(nx.ancestors(g, dataset_id))
        return {n for n in upstream if g.in_degree(n) == 0}

    def find_sinks(self, kg: KnowledgeGraph, dataset_id: str) -> Set[str]:
        """
        Return all downstream sink datasets (out_degree == 0) reachable from dataset_id.
        """
        g = kg.lineage_graph
        if dataset_id not in g:
            return set()
        downstream: Set[str] = set(nx.descendants(g, dataset_id))
        return {n for n in downstream if g.out_degree(n) == 0}

