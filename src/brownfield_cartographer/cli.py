import json
import logging
import re
import subprocess
import tempfile
from pathlib import Path
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
) -> None:
    """
    Run full analysis (Surveyor + Hydrologist) over the target repository.
    Accepts a local path or a GitHub URL (clones the repo if needed).
    """
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

    navigator = NavigatorAgent(kg)
    result = navigator.inspect_dataset(dataset_id)

    if not result.upstream and not result.downstream:
        typer.echo(f"No lineage information found for dataset '{dataset_id}'.")
        raise typer.Exit(code=0)

    if json_output:
        navigator = NavigatorAgent(kg)
        downstream = (
            navigator.mart_downstream_datasets(dataset_id) if mart_only else result.downstream
        )
        payload = {
            "target": result.target,
            "upstream": result.upstream,
            "downstream": downstream,
        }
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return

    typer.echo(f"Dataset: {result.target}")
    typer.echo("")
    typer.echo(f"Upstream ({len(result.upstream)}):")
    for node in result.upstream:
        typer.echo(f"- {node}")
    typer.echo("")
    typer.echo(f"Downstream ({len(result.downstream)}):")
    for node in result.downstream:
        typer.echo(f"- {node}")


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
) -> None:
    """
    Inspect upstream and downstream dependencies for a given module.
    """
    repo, out_dir = _resolve_paths(repo_path, output_dir)
    kg = _ensure_graphs(repo, out_dir)

    navigator = NavigatorAgent(kg)
    result = navigator.inspect_module(module_id)

    if not result.upstream and not result.downstream:
        typer.echo(f"No module dependency information found for module '{module_id}'.")
        raise typer.Exit(code=0)

    if json_output:
        payload = {
            "target": result.target,
            "upstream": result.upstream,
            "downstream": result.downstream,
        }
        typer.echo(json.dumps(payload, indent=2, sort_keys=True))
        return

    typer.echo(f"Module: {result.target}")
    typer.echo("")
    typer.echo(f"Upstream ({len(result.upstream)}):")
    for node in result.upstream:
        typer.echo(f"- {node}")
    typer.echo("")
    typer.echo(f"Downstream ({len(result.downstream)}):")
    for node in result.downstream:
        typer.echo(f"- {node}")


if __name__ == "__main__":  # pragma: no cover
    app()

