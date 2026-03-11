from __future__ import annotations

from pathlib import Path

from ..analyzers.tree_sitter_analyzer import analyze_python_module
from ..graph.knowledge_graph import KnowledgeGraph
from ..models.edges import ModuleDependencyEdge


IGNORED_DIR_NAMES = {".git", ".venv", "__pycache__", ".mypy_cache", ".pytest_cache"}


class SurveyorAgent:
    """
    Static structure agent that constructs a module dependency graph.
    """

    def run(self, repo_path: Path, kg: KnowledgeGraph) -> None:
        for path in repo_path.rglob("*.py"):
            if any(part in IGNORED_DIR_NAMES for part in path.parts):
                continue

            module_node = analyze_python_module(path)
            kg.add_module_node(module_node)

            for imported in module_node.imports:
                edge = ModuleDependencyEdge(
                    id=f"{module_node.id}->{imported}",
                    source_module_id=module_node.id,
                    target_module_id=imported,
                    reason="import",
                    evidence=module_node.evidence,
                )
                kg.add_module_edge(edge)

