from pathlib import Path
from typing import Literal

import typer

from .agents.archivist import ArchivistAgent
from .agents.navigator import NavigatorAgent
from .graph.knowledge_graph import KnowledgeGraph
from .orchestrator import Orchestrator


app = typer.Typer(help="Brownfield Cartographer CLI.")


def _resolve_paths(repo_path: str, output_dir: str) -> tuple[Path, Path]:
    repo = Path(repo_path).expanduser().resolve()
    out_dir = Path(output_dir).expanduser().resolve()
    if not repo.exists():
        typer.echo(f"Repository path does not exist: {repo}", err=True)
        raise typer.Exit(code=1)
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
) -> None:
    """
    Run full analysis (Surveyor + Hydrologist) over the target repository.
    """
    repo, out_dir = _resolve_paths(repo_path, output_dir)

    orchestrator = Orchestrator(repo_path=repo, output_dir=out_dir, output_format=format)

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
) -> None:
    """
    Generate a Day-One onboarding brief and CODEBASE overview.

    If graphs are missing, this will first run a full analysis.
    """
    repo, out_dir = _resolve_paths(repo_path, output_dir)

    kg = _ensure_graphs(repo, out_dir)

    archivist = ArchivistAgent(repo_path=repo, output_dir=out_dir)
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

    typer.echo(f"Dataset: {result.target}")
    typer.echo("")
    typer.echo(f"Upstream ({len(result.upstream)}):")
    for node in result.upstream:
        typer.echo(f"- {node}")
    typer.echo("")
    typer.echo(f"Downstream ({len(result.downstream)}):")
    for node in result.downstream:
        typer.echo(f"- {node}")


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

