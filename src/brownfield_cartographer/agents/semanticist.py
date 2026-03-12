from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Protocol, runtime_checkable

import networkx as nx

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


@runtime_checkable
class LLMClient(Protocol):
    """
    Protocol for an external LLM client that can be used to refine or replace
    the deterministic summaries produced by SemanticistAgent.
    """

    def summarize(self, prompt: str) -> str:  # pragma: no cover - interface only
        ...


@dataclass
class DayOneAnswers:
    main_ingestion_path: str
    critical_datasets: str
    blast_radius: str
    business_logic_locations: str
    most_active_files: str


class DayOneSemanticist(SemanticistAgent):
    """
    Extension of SemanticistAgent that computes structured answers aligned with
    the five Day-One onboarding questions.
    """

    def compute_day_one_answers(self, kg: KnowledgeGraph) -> DayOneAnswers:
        # Reuse simple heuristics based on graph structure and semantic summaries.
        lineage = kg.lineage_graph
        modules = kg.module_graph

        # 1. Main ingestion path (source nodes with outgoing edges).
        if lineage.number_of_nodes() == 0:
            main_ingestion = "No lineage graph detected; run `cartography analyze` first."
        else:
            sources = [n for n in lineage.nodes if lineage.in_degree(n) == 0 and lineage.out_degree(n) > 0]
            if sources:
                names = ", ".join(sorted(lineage.nodes[s].get("name", s) for s in sources))
                main_ingestion = f"Initial ingestion appears to start from: {names}."
            else:
                main_ingestion = "No clear source datasets found in the lineage graph."

        # 2. Critical datasets by downstream fan-out.
        if lineage.number_of_nodes() == 0:
            critical = "No datasets discovered yet."
        else:
            by_out_degree = sorted(lineage.nodes, key=lambda n: lineage.out_degree(n), reverse=True)[:5]
            if by_out_degree:
                parts = [
                    f"{lineage.nodes[n].get('name', n)} (downstream count={lineage.out_degree(n)})"
                    for n in by_out_degree
                ]
                critical = "Top critical datasets by downstream fan-out: " + ", ".join(parts) + "."
            else:
                critical = "No downstream dependencies found."

        # 3. Blast radius via max descendants.
        if lineage.number_of_nodes() == 0:
            blast = "Blast radius cannot be computed without a lineage graph."
        else:
            best_node = None
            best_reach = -1
            for node in lineage.nodes:
                reach = len(nx.descendants(lineage, node))
                if reach > best_reach:
                    best_reach = reach
                    best_node = node
            if best_node is None or best_reach <= 0:
                blast = "No meaningful blast radius identified; graph may be sparse."
            else:
                name = lineage.nodes[best_node].get("name", best_node)
                blast = (
                    f"If `{name}` fails, up to {best_reach} downstream datasets could be impacted "
                    "according to the lineage graph."
                )

        # 4. Business logic locations via high function/class/import counts.
        if modules.number_of_nodes() == 0:
            logic = "No modules discovered yet."
        else:
            def score(node_id: str) -> int:
                attrs = modules.nodes[node_id]
                return (
                    len(attrs.get("functions", []))
                    + len(attrs.get("classes", []))
                    + len(attrs.get("imports", []))
                )

            ranked = sorted(modules.nodes, key=score, reverse=True)[:5]
            parts = []
            for nid in ranked:
                attrs = modules.nodes[nid]
                parts.append(
                    f"{nid} (functions={len(attrs.get('functions', []))}, "
                    f"classes={len(attrs.get('classes', []))}, imports={len(attrs.get('imports', []))})"
                )
            logic = "Likely business-logic-heavy modules: " + ", ".join(parts) + "."

        # 5. Most active files from recent_commit_count metadata.
        if modules.number_of_nodes() == 0:
            active = "No modules discovered yet."
        else:
            modules_with_activity: List[tuple[str, int]] = []
            for node_id, attrs in modules.nodes(data=True):
                metadata = attrs.get("metadata") or {}
                commit_count = int(metadata.get("recent_commit_count", 0))
                modules_with_activity.append((node_id, commit_count))
            modules_with_activity.sort(key=lambda x: x[1], reverse=True)
            top = [m for m in modules_with_activity if m[1] > 0][:5]
            if not top:
                active = "No git activity metadata found; run in a git repo for change velocity signals."
            else:
                parts = [f"{m} ({c} commits in recent window)" for m, c in top]
                active = "Most active modules by recent git commits: " + ", ".join(parts) + "."

        return DayOneAnswers(
            main_ingestion_path=main_ingestion,
            critical_datasets=critical,
            blast_radius=blast,
            business_logic_locations=logic,
            most_active_files=active,
        )

