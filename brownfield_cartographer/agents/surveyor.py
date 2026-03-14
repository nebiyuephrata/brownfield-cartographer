from __future__ import annotations

import logging
import subprocess
from pathlib import Path
from typing import Iterable, List, Sequence, Set

import networkx as nx

from ..analyzers.tree_sitter_analyzer import analyze_python_module
from ..graph.knowledge_graph import KnowledgeGraph
from ..models.edges import ModuleDependencyEdge
from ..models.nodes import ModuleNode


logger = logging.getLogger(__name__)

IGNORED_DIR_NAMES = {".git", ".venv", "__pycache__", ".mypy_cache", ".pytest_cache"}

DEFAULT_GIT_VELOCITY_DAYS = 30


def _is_ignored(path: Path, ignore_globs: Sequence[str]) -> bool:
    if any(part in IGNORED_DIR_NAMES for part in path.parts):
        return True
    return any(path.match(pattern) for pattern in ignore_globs)


class SurveyorAgent:
    """
    Static structure agent that constructs a module dependency graph and runs
    analytical passes: PageRank, git change velocity, dead-code candidates,
    and circular dependency detection.
    """

    def __init__(
        self,
        ignore_globs: Iterable[str] | None = None,
        git_velocity_days: int = DEFAULT_GIT_VELOCITY_DAYS,
    ) -> None:
        self.ignore_globs: List[str] = list(ignore_globs) if ignore_globs is not None else []
        self.git_velocity_days = git_velocity_days

    def _recent_commit_count(self, repo_path: Path, file_path: Path) -> int:
        """
        Best-effort git-based change velocity for a single file over a configurable window.

        If the repository is not a git repo or git is unavailable, this returns 0.
        """
        git_dir = repo_path / ".git"
        if not git_dir.exists():
            return 0
        try:
            rel_path = file_path.relative_to(repo_path)
        except ValueError:
            rel_path = file_path
        try:
            result = subprocess.run(
                [
                    "git",
                    "-C",
                    str(repo_path),
                    "log",
                    "--pretty=oneline",
                    f"--since={self.git_velocity_days} days ago",
                    "--",
                    str(rel_path),
                ],
                stdout=subprocess.PIPE,
                stderr=subprocess.DEVNULL,
                text=True,
                check=False,
            )
        except Exception:
            return 0
        if result.returncode != 0 or not result.stdout:
            return 0
        return len([line for line in result.stdout.splitlines() if line.strip()])

    def _attach_analytics(self, kg: KnowledgeGraph) -> None:
        """
        Run PageRank, dead-code detection, and circular dependency detection;
        attach results to node attributes (e.g. pagerank, is_dead_code_candidate,
        in_cycle) and set change_velocity_30d from metadata.
        """
        g = kg.module_graph
        if g.number_of_nodes() == 0:
            return

        for nid, attrs in g.nodes(data=True):
            meta = attrs.get("metadata") or {}
            commits = int(meta.get("recent_commit_count", 0))
            g.nodes[nid]["change_velocity_30d"] = float(commits)
            g.nodes[nid]["is_dead_code_candidate"] = False

        try:
            pagerank = nx.pagerank(g)
            for nid, score in pagerank.items():
                g.nodes[nid]["pagerank"] = score
        except Exception:
            pass

        importers: dict[str, Set[str]] = {}
        for u, v in g.edges():
            importers.setdefault(v, set()).add(u)
        for nid, attrs in g.nodes(data=True):
            exports = set(attrs.get("functions", []) or []) | set(attrs.get("classes", []) or [])
            if exports and nid not in importers:
                g.nodes[nid]["is_dead_code_candidate"] = True

        try:
            sccs = list(nx.strongly_connected_components(g))
            cycles = [c for c in sccs if len(c) > 1]
            for cycle in cycles:
                for nid in cycle:
                    g.nodes[nid]["in_cycle"] = True
                    g.nodes[nid]["cycle_members"] = list(cycle)
        except Exception:
            pass

    def run(self, repo_path: Path, kg: KnowledgeGraph) -> None:
        """
        Walk the repository and populate the module graph. Per-file errors are
        logged and skipped so partial results are always produced. After building
        the graph, runs PageRank, git velocity, dead-code detection, and circular
        dependency detection and attaches results to nodes.
        """
        for path in repo_path.rglob("*.py"):
            if _is_ignored(path, self.ignore_globs):
                continue
            try:
                module_node: ModuleNode = analyze_python_module(path)
            except Exception as exc:
                logger.warning("Skipping %s: %s", path, exc)
                continue

            commit_count = self._recent_commit_count(repo_path, path)
            if commit_count > 0:
                metadata = dict(module_node.metadata)
                metadata["recent_commit_count"] = commit_count
                module_node.metadata = metadata
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

        self._attach_analytics(kg)

