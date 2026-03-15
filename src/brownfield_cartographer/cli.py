import json
import logging
import os
import re
import subprocess
import tempfile
from pathlib import Path
from collections import deque
from typing import Literal

import typer

from .agents.archivist import ArchivistAgent
from .agents.navigator import NavigatorAgent
from .graph.knowledge_graph import KnowledgeGraph
from .orchestrator import Orchestrator


app = typer.Typer(help="Brownfield Cartographer CLI.")

GITHUB_URL_PATTERN = re.compile(
    r"^(https?://github\.com/[\w.-]+/[\w.-]+?)(?:\.git)?/?$|^git@github\.com:([\w.-]+/[\w.-]+?)(?:\.git)?$"
)

def _iter_env_paths(start: Path) -> list[Path]:
    """
    Walk upwards from a start directory and return candidate .env paths.
    """
    paths: list[Path] = []
    cur = start.resolve()
    for _ in range(6):
        paths.append(cur / ".env")
        # stop if a project marker exists
        if (cur / "pyproject.toml").exists() or (cur / ".git").exists():
            break
        if cur.parent == cur:
            break
        cur = cur.parent
    return paths


def _load_dotenv(path: Path | None = None) -> None:
    """
    Minimal .env loader (KEY=VALUE per line). Does not override existing env vars.
    Searches CWD and repo root near this file if no explicit path is given.
    """
    candidates: list[Path] = []
    if path is not None:
        candidates = [path]
    else:
        candidates.extend(_iter_env_paths(Path.cwd()))
        # also search from this file's directory (repo root via src/)
        candidates.extend(_iter_env_paths(Path(__file__).resolve().parent))

    seen: set[Path] = set()
    for env_path in candidates:
        if env_path in seen:
            continue
        seen.add(env_path)
        if not env_path.exists():
            continue
        for raw in env_path.read_text(encoding="utf-8").splitlines():
            line = raw.strip()
            if not line or line.startswith("#") or "=" not in line:
                continue
            key, value = line.split("=", 1)
            key = key.strip()
            value = value.strip().strip('"').strip("'")
            if key and key not in os.environ:
                os.environ[key] = value


def _resolve_repo_path(repo_path: str) -> Path:
    """
    Accept a local path or a GitHub URL. If GitHub URL, clone into a temporary
    directory and return that path; otherwise resolve and validate the local path.
    """
    repo_path = repo_path.strip()
    match = GITHUB_URL_PATTERN.match(repo_path)
    if match:
        url = match.group(1) or f"https://github.com/{match.group(2)}"
        if not url.endswith(".git"):
            url = url.rstrip("/") + ".git"
        tmp = tempfile.mkdtemp(prefix="cartography_repo_")
        try:
            result = subprocess.run(
                ["git", "clone", "--depth", "1", url, tmp],
                capture_output=True,
                text=True,
                timeout=120,
            )
            if result.returncode != 0:
                typer.echo(f"Clone failed: {result.stderr or result.stdout}", err=True)
                raise typer.Exit(code=1)
            return Path(tmp).resolve()
        except subprocess.TimeoutExpired:
            typer.echo("Clone timed out.", err=True)
            raise typer.Exit(code=1)
        except FileNotFoundError:
            typer.echo("Git not found; cannot clone GitHub URL.", err=True)
            raise typer.Exit(code=1)

    repo = Path(repo_path).expanduser().resolve()
    if not repo.exists():
        typer.echo(f"Repository path does not exist: {repo}", err=True)
        raise typer.Exit(code=1)
    return repo


def _resolve_paths(repo_path: str, output_dir: str) -> tuple[Path, Path]:
    repo = _resolve_repo_path(repo_path)
    out_dir = Path(output_dir).expanduser().resolve()
    out_dir.mkdir(parents=True, exist_ok=True)
    return repo, out_dir


def _relpath(path_str: str, repo: Path) -> str:
    try:
        p = Path(path_str)
        return str(p.resolve().relative_to(repo.resolve()))
    except Exception:
        return path_str


def _format_evidence(evidence: list[dict] | None, repo: Path, max_items: int = 1) -> str:
    if not evidence:
        return ""
    parts: list[str] = []
    for ev in evidence[:max_items]:
        fp = _relpath(str(ev.get("file_path", "")), repo)
        ls = ev.get("line_start")
        le = ev.get("line_end")
        method = ev.get("method")
        loc = f"{fp}:{ls}-{le}" if ls and le else fp
        parts.append(f"{loc}" + (f" ({method})" if method else ""))
    return "; ".join(parts)


def _bfs_nodes(
    g, start: str, direction: Literal["up", "down"], max_nodes: int
) -> dict[str, int]:
    """
    Return a mapping of reachable node -> hop distance from `start`.
    direction='up' follows predecessors; direction='down' follows successors.
    """
    if start not in g:
        return {}
    depths: dict[str, int] = {start: 0}
    q: deque[str] = deque([start])
    while q and len(depths) < max_nodes:
        cur = q.popleft()
        nxts = g.predecessors(cur) if direction == "up" else g.successors(cur)
        for nxt in nxts:
            if nxt in depths:
                continue
            depths[nxt] = depths[cur] + 1
            q.append(nxt)
            if len(depths) >= max_nodes:
                break
    return depths


def _normalize_module_id(repo: Path, module_id: str) -> str:
    candidate = Path(module_id)
    if not candidate.is_absolute():
        candidate = repo / candidate
    if candidate.exists() and candidate.is_file() and candidate.suffix == ".py":
        try:
            rel = candidate.resolve().relative_to(repo.resolve())
            return str(rel).replace("/", ".").removesuffix(".py")
        except Exception:
            return module_id
    return module_id


def _ensure_graphs(repo: Path, out_dir: Path) -> KnowledgeGraph:
    module_graph_path = out_dir / "module_graph.json"
    lineage_graph_path = out_dir / "lineage_graph.json"

    if not module_graph_path.exists() or not lineage_graph_path.exists():
        typer.echo("Graphs not found; running full analysis first...", err=True)
        orchestrator = Orchestrator(repo_path=repo, output_dir=out_dir, output_format="json")
        orchestrator.run_all()

    return KnowledgeGraph.load_from_paths(
        module_graph_path=module_graph_path,
        lineage_graph_path=lineage_graph_path,
    )


@app.command()
def analyze(
    repo_path: str = typer.Argument(..., help="Path to the target repository."),
    output_dir: str = typer.Option(
        ".cartography",
        "--output-dir",
        "-o",
        help="Directory where analysis artifacts will be written.",
    ),
    format: Literal["json"] = typer.Option(
        "json",
        "--format",
        "-f",
        help="Output format for graphs (currently only 'json' is supported).",
    ),
    skip_lineage: bool = typer.Option(
        False,
        "--skip-lineage",
        help="Skip SQL/data lineage analysis (HydrologistAgent) for faster iteration.",
    ),
    semantic: bool = typer.Option(
        True,
        "--semantic/--no-semantic",
        help="Enable or disable semantic summaries (SemanticistAgent).",
    ),
    emit_docs: bool = typer.Option(
        False,
        "--emit-docs",
        help="Also generate CODEBASE.md and ONBOARDING_BRIEF.md into --output-dir.",
    ),
) -> None:
    """
    Run full analysis (Surveyor + Hydrologist) over the target repository.
    Accepts a local path or a GitHub URL (clones the repo if needed).
    """
    _load_dotenv()
    logging.basicConfig(level=logging.INFO, format="%(message)s")
    repo, out_dir = _resolve_paths(repo_path, output_dir)

    orchestrator = Orchestrator(
        repo_path=repo,
        output_dir=out_dir,
        output_format=format,
        run_surveyor=True,
        run_hydrologist=not skip_lineage,
        enable_semanticist=semantic,
    )

    try:
        orchestrator.run_all()
    except Exception as exc:  # pragma: no cover - defensive
        typer.echo(f"Analysis failed: {exc}", err=True)
        raise typer.Exit(code=1)

    if emit_docs:
        kg = KnowledgeGraph.load_from_paths(
            module_graph_path=out_dir / "module_graph.json",
            lineage_graph_path=out_dir / "lineage_graph.json",
        )
        ArchivistAgent(repo_path=repo, output_dir=out_dir).write_codebase_docs(kg)
        typer.echo(f"Docs generated: {out_dir / 'CODEBASE.md'}")

    typer.echo(f"Analysis complete. Artifacts written to: {out_dir}")


@app.command()
def brief(
    repo_path: str = typer.Argument(..., help="Path to the target repository."),
    output_dir: str = typer.Option(
        ".cartography",
        "--output-dir",
        "-o",
        help="Directory where analysis artifacts will be read from or written to.",
    ),
    format: Literal["markdown", "json-summary"] = typer.Option(
        "markdown",
        "--format",
        "-f",
        help="Output format for the onboarding brief (markdown file paths or a compact JSON summary).",
    ),
) -> None:
    """
    Generate a Day-One onboarding brief and CODEBASE overview.

    If graphs are missing, this will first run a full analysis.
    """
    repo, out_dir = _resolve_paths(repo_path, output_dir)

    kg = _ensure_graphs(repo, out_dir)

    archivist = ArchivistAgent(repo_path=repo, output_dir=out_dir)

    if format == "json-summary":
        answers = archivist.infer_onboarding_answers(kg)
        payload = {
            "primary_ingestion_path": answers.main_ingestion_path,
            "critical_datasets": answers.critical_datasets,
            "blast_radius": answers.blast_radius,
            "business_logic_locations": answers.business_logic_locations,
            "most_active_files": answers.most_active_files,
        }
        # Still materialize the markdown artifacts on disk for humans and CI logs.
        archivist.write_codebase_docs(kg)
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return

    codebase_path, onboarding_path, recon_path = archivist.write_codebase_docs(kg)

    typer.echo(
        "Onboarding artifacts generated:\n"
        f"- {codebase_path}\n"
        f"- {onboarding_path}\n"
        f"- {recon_path}"
    )


@app.command("lineage")
def lineage_command(
    repo_path: str = typer.Argument(..., help="Path to the target repository."),
    dataset_id: str = typer.Argument(..., help="Dataset ID to inspect in the lineage graph."),
    output_dir: str = typer.Option(
        ".cartography",
        "--output-dir",
        "-o",
        help="Directory where analysis artifacts will be read from or written to.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit lineage information as JSON instead of human-readable text.",
    ),
    transitive: bool = typer.Option(
        False,
        "--transitive",
        help="Show full transitive upstream/downstream closure, not just immediate neighbors.",
    ),
    evidence: bool = typer.Option(
        False,
        "--evidence",
        help="Include file/line evidence for each edge when available.",
    ),
    max_nodes: int = typer.Option(
        200,
        "--max-nodes",
        help="Safety limit on nodes visited during transitive traversal.",
    ),
    mart_only: bool = typer.Option(
        False,
        "--mart-only",
        help="When set, only show downstream mart datasets in the JSON payload.",
    ),
) -> None:
    """
    Inspect upstream and downstream lineage for a given dataset.
    """
    repo, out_dir = _resolve_paths(repo_path, output_dir)
    kg = _ensure_graphs(repo, out_dir)
    if dataset_id not in kg.lineage_graph and ":" not in dataset_id:
        resolved = kg.get_dataset_by_name(dataset_id)
        if resolved:
            dataset_id = resolved

    navigator = NavigatorAgent(kg)
    if transitive:
        up_depth = _bfs_nodes(kg.lineage_graph, dataset_id, "up", max_nodes=max_nodes)
        down_depth = _bfs_nodes(kg.lineage_graph, dataset_id, "down", max_nodes=max_nodes)
        upstream_nodes = sorted([n for n in up_depth if n != dataset_id], key=lambda n: (-up_depth[n], n))
        downstream_nodes = sorted([n for n in down_depth if n != dataset_id], key=lambda n: (down_depth[n], n))
        result = type("Tmp", (), {"target": dataset_id, "upstream": upstream_nodes, "downstream": downstream_nodes})()
    else:
        result = navigator.inspect_dataset(dataset_id)

    if not result.upstream and not result.downstream:
        typer.echo(f"No lineage information found for dataset '{dataset_id}'.")
        raise typer.Exit(code=0)

    if json_output:
        downstream = navigator.mart_downstream_datasets(dataset_id) if mart_only else result.downstream
        payload_edges = []
        if transitive:
            nodeset = set([dataset_id, *result.upstream, *downstream])
            for u, v, attrs in kg.lineage_graph.edges(data=True):
                if u in nodeset and v in nodeset:
                    payload_edges.append(
                        {
                            "source": u,
                            "target": v,
                            "transformation_id": attrs.get("transformation_id"),
                            "metadata": attrs.get("metadata") or {},
                            "evidence": attrs.get("evidence") or [],
                        }
                    )
        payload = {
            "target": result.target,
            "upstream": result.upstream,
            "downstream": downstream,
            "edges": payload_edges,
        }
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return

    typer.echo(f"Dataset: {result.target}")
    typer.echo("")
    typer.echo(f"Upstream ({len(result.upstream)})" + (" [transitive]" if transitive else "") + ":")
    for node in result.upstream:
        typer.echo(f"- {node}")
    typer.echo("")
    typer.echo(f"Downstream ({len(result.downstream)})" + (" [transitive]" if transitive else "") + ":")
    for node in result.downstream:
        typer.echo(f"- {node}")

    if evidence:
        typer.echo("")
        typer.echo("Evidence (edges):")
        nodeset = set([dataset_id, *result.upstream, *result.downstream])
        shown = 0
        for u, v, attrs in kg.lineage_graph.edges(data=True):
            if u not in nodeset or v not in nodeset:
                continue
            ev = _format_evidence(attrs.get("evidence"), repo)
            meta = attrs.get("metadata") or {}
            op = meta.get("operation") or ""
            extra = f" op={op}" if op else ""
            typer.echo(f"- {u} -> {v}{extra}" + (f"  ({ev})" if ev else ""))
            shown += 1
            if shown >= 200:
                typer.echo("- ... (truncated)")
                break


@app.command("path")
def path_command(
    repo_path: str = typer.Argument(..., help="Path to the target repository."),
    source_id: str = typer.Argument(..., help="Source dataset ID in the lineage graph."),
    target_id: str = typer.Argument(..., help="Target dataset ID in the lineage graph."),
    output_dir: str = typer.Option(
        ".cartography",
        "--output-dir",
        "-o",
        help="Directory where analysis artifacts will be read from or written to.",
    ),
) -> None:
    """
    Show a simple lineage path between two datasets, if one exists.
    """
    repo, out_dir = _resolve_paths(repo_path, output_dir)
    kg = _ensure_graphs(repo, out_dir)

    import networkx as nx  # local import to avoid hard dependency for non-path commands

    g = kg.lineage_graph
    if source_id not in g or target_id not in g:
        typer.echo("Either source or target dataset ID is not present in the lineage graph.")
        raise typer.Exit(code=1)

    try:
        path = nx.shortest_path(g, source=source_id, target=target_id)
    except nx.NetworkXNoPath:
        typer.echo(f"No path found from '{source_id}' to '{target_id}'.")
        raise typer.Exit(code=0)

    typer.echo(" -> ".join(path))


@app.command("map")
def map_command(
    repo_path: str = typer.Argument(..., help="Path to the target repository."),
    module_id: str = typer.Argument(..., help="Module ID to inspect in the module graph."),
    output_dir: str = typer.Option(
        ".cartography",
        "--output-dir",
        "-o",
        help="Directory where analysis artifacts will be read from or written to.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit module dependency information as JSON instead of human-readable text.",
    ),
    transitive: bool = typer.Option(
        False,
        "--transitive",
        help="Show full transitive upstream/downstream closure, not just immediate neighbors.",
    ),
    evidence: bool = typer.Option(
        False,
        "--evidence",
        help="Include file/line evidence and dependency reason when available.",
    ),
    max_nodes: int = typer.Option(
        400,
        "--max-nodes",
        help="Safety limit on nodes visited during transitive traversal.",
    ),
) -> None:
    """
    Inspect upstream and downstream dependencies for a given module.
    """
    repo, out_dir = _resolve_paths(repo_path, output_dir)
    kg = _ensure_graphs(repo, out_dir)
    module_id = _normalize_module_id(repo, module_id)

    navigator = NavigatorAgent(kg)
    if transitive:
        up_depth = _bfs_nodes(kg.module_graph, module_id, "up", max_nodes=max_nodes)
        down_depth = _bfs_nodes(kg.module_graph, module_id, "down", max_nodes=max_nodes)
        upstream_nodes = sorted([n for n in up_depth if n != module_id], key=lambda n: (-up_depth[n], n))
        downstream_nodes = sorted([n for n in down_depth if n != module_id], key=lambda n: (down_depth[n], n))
        result = type("Tmp", (), {"target": module_id, "upstream": upstream_nodes, "downstream": downstream_nodes})()
    else:
        result = navigator.inspect_module(module_id)

    if not result.upstream and not result.downstream:
        typer.echo(f"No module dependency information found for module '{module_id}'.")
        raise typer.Exit(code=0)

    if json_output:
        payload_edges = []
        if transitive:
            nodeset = set([module_id, *result.upstream, *result.downstream])
            for u, v, attrs in kg.module_graph.edges(data=True):
                if u in nodeset and v in nodeset:
                    payload_edges.append(
                        {
                            "source": u,
                            "target": v,
                            "reason": attrs.get("reason"),
                            "metadata": attrs.get("metadata") or {},
                            "evidence": attrs.get("evidence") or [],
                        }
                    )
        payload = {
            "target": result.target,
            "upstream": result.upstream,
            "downstream": result.downstream,
            "edges": payload_edges,
        }
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return

    typer.echo(f"Module: {result.target}")
    typer.echo("")
    typer.echo(f"Upstream ({len(result.upstream)})" + (" [transitive]" if transitive else "") + ":")
    for node in result.upstream:
        typer.echo(f"- {node}")
    typer.echo("")
    typer.echo(f"Downstream ({len(result.downstream)})" + (" [transitive]" if transitive else "") + ":")
    for node in result.downstream:
        typer.echo(f"- {node}")

    if evidence:
        typer.echo("")
        typer.echo("Evidence (edges):")
        nodeset = set([module_id, *result.upstream, *result.downstream])
        shown = 0
        for u, v, attrs in kg.module_graph.edges(data=True):
            if u not in nodeset or v not in nodeset:
                continue
            ev = _format_evidence(attrs.get("evidence"), repo)
            reason = attrs.get("reason") or ""
            extra = f" reason={reason}" if reason else ""
            typer.echo(f"- {u} -> {v}{extra}" + (f"  ({ev})" if ev else ""))
            shown += 1
            if shown >= 200:
                typer.echo("- ... (truncated)")
                break


@app.command("blast")
def blast_command(
    repo_path: str = typer.Argument(..., help="Path to the target repository."),
    module: str = typer.Argument(..., help="Module id or a path to a .py file to assess impact for."),
    output_dir: str = typer.Option(
        ".cartography",
        "--output-dir",
        "-o",
        help="Directory where analysis artifacts will be read from or written to.",
    ),
    json_output: bool = typer.Option(
        False,
        "--json",
        help="Emit blast radius information as JSON instead of human-readable text.",
    ),
    max_nodes: int = typer.Option(
        400,
        "--max-nodes",
        help="Safety limit on nodes visited during traversal.",
    ),
    evidence: bool = typer.Option(
        False,
        "--evidence",
        help="Include file/line evidence and dependency reason when available.",
    ),
) -> None:
    """
    Compute the blast radius (reverse dependencies) for a given module.

    This reports all modules that depend on the selected module (transitively),
    i.e. the likely impact set if the module changes.
    """
    repo, out_dir = _resolve_paths(repo_path, output_dir)
    kg = _ensure_graphs(repo, out_dir)

    module_id = _normalize_module_id(repo, module)
    depths = _bfs_nodes(kg.module_graph, module_id, "up", max_nodes=max_nodes)
    dependents = sorted([n for n in depths if n != module_id], key=lambda n: (depths[n], n))

    if json_output:
        nodeset = set([module_id, *dependents])
        payload_edges = []
        for u, v, attrs in kg.module_graph.edges(data=True):
            if u in nodeset and v in nodeset:
                payload_edges.append(
                    {
                        "source": u,
                        "target": v,
                        "reason": attrs.get("reason"),
                        "metadata": attrs.get("metadata") or {},
                        "evidence": attrs.get("evidence") or [],
                    }
                )
        typer.echo(
            json.dumps(
                {"target": module_id, "dependents": dependents, "edges": payload_edges},
                indent=2,
                sort_keys=True,
            )
        )
        return

    typer.echo(f"Module: {module_id}")
    typer.echo("")
    typer.echo(f"Dependents ({len(dependents)}) [transitive]:")
    for node in dependents:
        typer.echo(f"- {node}")

    if evidence:
        typer.echo("")
        typer.echo("Evidence (edges):")
        nodeset = set([module_id, *dependents])
        shown = 0
        for u, v, attrs in kg.module_graph.edges(data=True):
            if u not in nodeset or v not in nodeset:
                continue
            ev = _format_evidence(attrs.get("evidence"), repo)
            reason = attrs.get("reason") or ""
            extra = f" reason={reason}" if reason else ""
            typer.echo(f"- {u} -> {v}{extra}" + (f"  ({ev})" if ev else ""))
            shown += 1
            if shown >= 200:
                typer.echo("- ... (truncated)")
                break


if __name__ == "__main__":  # pragma: no cover
    import inspect
    import sys

    # This repo sometimes runs with a tiny local `typer` shim (see `typer/` at repo root)
    # where `Typer.__call__` expects `argv`. Real Typer (click-backed) does not.
    try:
        sig = inspect.signature(app.__call__)
        params = list(sig.parameters.values())
        has_varargs = any(
            p.kind in (inspect.Parameter.VAR_POSITIONAL, inspect.Parameter.VAR_KEYWORD)
            for p in params
        )
        if not has_varargs and len(params) == 1:
            raise SystemExit(app(sys.argv[1:]))
    except (ValueError, TypeError):
        pass

    app()
