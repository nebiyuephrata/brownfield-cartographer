from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Dict, Iterable, List, Tuple, Optional

import networkx as nx

from ..graph.knowledge_graph import KnowledgeGraph
from .semanticist import DayOneAnswers


ONBOARDING_FILENAME = "ONBOARDING_BRIEF.md"
CODEBASE_FILENAME = "CODEBASE.md"
RECON_FILENAME = "RECONNAISSANCE.md"


@dataclass
class OnboardingAnswers:
    main_ingestion_path: str
    critical_datasets: str
    blast_radius: str
    business_logic_locations: str
    most_active_files: str


class ArchivistAgent:
    """
    Documentation-focused agent.

    Synthesizes CODEBASE.md and an onboarding brief from the graphs and any
    semantic metadata. All assertions are backed by pointers to concrete
    files and nodes in the graphs when possible.
    """

    def __init__(self, repo_path: Path, output_dir: Path) -> None:
        self.repo_path = repo_path
        self.output_dir = output_dir

    # ----- Public API -------------------------------------------------

    def write_codebase_docs(
        self,
        kg: KnowledgeGraph,
        semantic_answers: Optional[DayOneAnswers] = None,
    ) -> Tuple[Path, Path, Path]:
        """
        Write CODEBASE.md, ONBOARDING_BRIEF.md, and a RECONNAISSANCE.md
        skeleton (if missing). Returns their paths.
        """
        codebase_path = self.output_dir / CODEBASE_FILENAME
        onboarding_path = self.output_dir / ONBOARDING_FILENAME
        # Keep all artifacts in `output_dir` so analyzing a read-only target repo works.
        recon_path = self.output_dir / RECON_FILENAME

        answers = semantic_answers or self.infer_onboarding_answers(kg)

        codebase_path.write_text(self._render_codebase_md(kg, answers), encoding="utf-8")
        onboarding_path.write_text(self._render_onboarding_md(answers), encoding="utf-8")

        if not recon_path.exists():
            recon_path.write_text(self._render_recon_skeleton(), encoding="utf-8")

        return codebase_path, onboarding_path, recon_path

    def infer_onboarding_answers(self, kg: KnowledgeGraph) -> OnboardingAnswers:
        """
        Public helper that infers the core Day-One onboarding answers from the graphs.
        """
        return self._infer_onboarding_answers(kg)

    # ----- Rendering helpers ------------------------------------------

    def _render_codebase_md(self, kg: KnowledgeGraph, answers: OnboardingAnswers) -> str:
        module_count = kg.module_graph.number_of_nodes()
        lineage_node_count = kg.lineage_graph.number_of_nodes()
        lineage_edge_count = kg.lineage_graph.number_of_edges()

        def _truncate(text: str, max_len: int = 180) -> str:
            if len(text) <= max_len:
                return text
            return text[: max_len - 3].rstrip() + "..."

        example_datasets = []
        for node_id, attrs in list(kg.lineage_graph.nodes(data=True))[:5]:
            example_datasets.append(f"- `{node_id}` (name={attrs.get('name', node_id)})")

        example_modules = []
        for node_id, attrs in list(kg.module_graph.nodes(data=True))[:5]:
            example_modules.append(f"- `{node_id}` (path={attrs.get('path', '')})")

        module_purpose = []
        for node_id, attrs in list(kg.module_graph.nodes(data=True))[:10]:
            meta = attrs.get("metadata") or {}
            summary = meta.get("semantic_summary")
            provider = meta.get("semantic_provider")
            if summary:
                suffix = f" [{provider}]" if provider else ""
                module_purpose.append(f"- `{node_id}`: {_truncate(summary)}{suffix}")

        dataset_purpose = []
        for node_id, attrs in list(kg.lineage_graph.nodes(data=True))[:10]:
            meta = attrs.get("metadata") or {}
            summary = meta.get("semantic_summary")
            provider = meta.get("semantic_provider")
            if summary:
                suffix = f" [{provider}]" if provider else ""
                dataset_purpose.append(
                    f"- `{attrs.get('name', node_id)}`: {_truncate(summary)}{suffix}"
                )

        lines = [
            "# CODEBASE Overview",
            "",
            f"- Total modules analyzed: **{module_count}**",
            f"- Total datasets in lineage graph: **{lineage_node_count}**",
            f"- Total lineage edges: **{lineage_edge_count}**",
            "",
            "## High-Level Architecture",
            "",
            "- Module graph nodes represent Python modules discovered by the Surveyor agent.",
            "- Lineage graph nodes represent datasets and transformations discovered by the Hydrologist agent.",
            "",
            "## Key Onboarding Answers (Summary)",
            "",
            f"- **Primary ingestion path**: {answers.main_ingestion_path}",
            f"- **Critical datasets**: {answers.critical_datasets}",
            f"- **Blast radius of failures**: {answers.blast_radius}",
            f"- **Business logic concentration**: {answers.business_logic_locations}",
            f"- **Most active files**: {answers.most_active_files}",
            "",
            "## Example Datasets (Evidence)",
            "",
            *(example_datasets or ["- (no datasets discovered)"]),
            "",
            "## Example Modules (Evidence)",
            "",
            *(example_modules or ["- (no modules discovered)"]),
            "",
            "## Module Purpose Index",
            "",
            *(module_purpose or ["- (no semantic summaries found)"]),
            "",
            "## Dataset Purpose Index",
            "",
            *(dataset_purpose or ["- (no semantic summaries found)"]),
            "",
            "## Evidence Sources",
            "",
            "- Module graph: `.cartography/module_graph.json`",
            "- Lineage graph: `.cartography/lineage_graph.json`",
        ]
        return "\n".join(lines)

    def _render_onboarding_md(self, answers: OnboardingAnswers) -> str:
        return "\n".join(
            [
                "# Day-One Onboarding Brief",
                "",
                "## 1. Primary Data Ingestion Path",
                answers.main_ingestion_path,
                "",
                "## 2. Most Critical Datasets",
                answers.critical_datasets,
                "",
                "## 3. Blast Radius of Failures",
                answers.blast_radius,
                "",
                "## 4. Where Business Logic Lives",
                answers.business_logic_locations,
                "",
                "## 5. Most Frequently Changing Files",
                answers.most_active_files,
                "",
                "> All statements above are derived from the module and lineage graphs; see `.cartography/*.json` for machine-readable evidence.",
            ]
        )

    def _render_recon_skeleton(self) -> str:
        return "\n".join(
            [
                "# Reconnaissance – Target Repository",
                "",
                "1. Primary Data Ingestion",
                "",
                "2. Critical Outputs",
                "",
                "3. Blast Radius",
                "",
                "4. Business Logic",
                "",
                "5. Most Active Files",
                "",
                "> This skeleton was auto-generated by Brownfield Cartographer. Fill in details from manual inspection and graph outputs.",
            ]
        )

    # ----- Inference helpers ------------------------------------------

    def _infer_onboarding_answers(self, kg: KnowledgeGraph) -> OnboardingAnswers:
        main_ingestion = self._infer_main_ingestion_path(kg)
        critical = self._infer_critical_datasets(kg)
        blast = self._infer_blast_radius(kg)
        logic = self._infer_business_logic_locations(kg)
        active = self._infer_most_active_files(kg)

        return OnboardingAnswers(
            main_ingestion_path=main_ingestion,
            critical_datasets=critical,
            blast_radius=blast,
            business_logic_locations=logic,
            most_active_files=active,
        )

    def _infer_main_ingestion_path(self, kg: KnowledgeGraph) -> str:
        g = kg.lineage_graph
        if g.number_of_nodes() == 0:
            return "No lineage graph detected yet. Run `cartography analyze` first."

        sources = [n for n in g.nodes if g.in_degree(n) == 0 and g.out_degree(n) > 0]
        if not sources:
            return "No clear source datasets found; inspect `.cartography/lineage_graph.json` for details."

        names = ", ".join(sorted(g.nodes[s].get("name", s) for s in sources))
        return f"Initial ingestion appears to start from: {names}."

    def _infer_critical_datasets(self, kg: KnowledgeGraph) -> str:
        g = kg.lineage_graph
        if g.number_of_nodes() == 0:
            return "No datasets discovered yet."

        by_out_degree = sorted(g.nodes, key=lambda n: g.out_degree(n), reverse=True)
        top = by_out_degree[:5]
        if not top:
            return "No downstream dependencies found."

        parts = [
            f"{g.nodes[n].get('name', n)} (downstream count={g.out_degree(n)})"
            for n in top
        ]
        return "Top critical datasets by downstream fan-out: " + ", ".join(parts) + "."

    def _infer_blast_radius(self, kg: KnowledgeGraph) -> str:
        g = kg.lineage_graph
        if g.number_of_nodes() == 0:
            return "Blast radius cannot be computed without a lineage graph."

        # Heuristic: pick node with max number of reachable descendants.
        best_node = None
        best_reach = -1
        for node in g.nodes:
            reach = len(nx.descendants(g, node))
            if reach > best_reach:
                best_reach = reach
                best_node = node

        if best_node is None or best_reach <= 0:
            return "No meaningful blast radius identified; graph may be sparse."

        name = g.nodes[best_node].get("name", best_node)
        return (
            f"If `{name}` fails, up to {best_reach} downstream datasets could be impacted "
            "according to the lineage graph."
        )

    def _infer_business_logic_locations(self, kg: KnowledgeGraph) -> str:
        g = kg.module_graph
        if g.number_of_nodes() == 0:
            return "No modules discovered yet."

        # Approximate \"business logic\" as modules with many functions/classes and imports.
        def score(node_id: str) -> int:
            attrs = g.nodes[node_id]
            return (
                len(attrs.get("functions", []))
                + len(attrs.get("classes", []))
                + len(attrs.get("imports", []))
            )

        ranked = sorted(g.nodes, key=score, reverse=True)[:5]
        parts = []
        for nid in ranked:
            attrs = g.nodes[nid]
            parts.append(
                f"{nid} (functions={len(attrs.get('functions', []))}, "
                f"classes={len(attrs.get('classes', []))}, imports={len(attrs.get('imports', []))})"
            )
        return "Likely business-logic-heavy modules: " + ", ".join(parts) + "."

    def _infer_most_active_files(self, kg: KnowledgeGraph) -> str:
        g = kg.module_graph
        if g.number_of_nodes() == 0:
            return "No modules discovered yet."

        modules_with_activity: List[Tuple[str, int]] = []
        for node_id, attrs in g.nodes(data=True):
            metadata = attrs.get("metadata") or {}
            commit_count = int(metadata.get("recent_commit_count", 0))
            modules_with_activity.append((node_id, commit_count))

        modules_with_activity.sort(key=lambda x: x[1], reverse=True)
        top = [m for m in modules_with_activity if m[1] > 0][:5]

        if not top:
            return "No git activity metadata found; run in a git repo for change velocity signals."

        parts = [f"{m} ({c} commits in recent window)" for m, c in top]
        return "Most active modules by recent git commits: " + ", ".join(parts) + "."
