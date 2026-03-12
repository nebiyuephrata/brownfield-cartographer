import json
from pathlib import Path

from typer.testing import CliRunner

from brownfield_cartographer import cli
from brownfield_cartographer.graph.knowledge_graph import KnowledgeGraph


runner = CliRunner()


def test_analyze_help_shows_expected_options():
    result = runner.invoke(cli.app, ["analyze", "--help"])
    assert result.exit_code == 0
    assert "Path to the target repository." in result.stdout
    assert "--output-dir" in result.stdout
    assert "--format" in result.stdout
    assert "--skip-lineage" in result.stdout
    # Typer renders boolean flag pairs as --semantic / --no-semantic
    assert "--semantic" in result.stdout
    assert "--no-semantic" in result.stdout


def test_brief_json_summary_uses_format_option(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    output_dir = tmp_path / ".cartography"
    output_dir.mkdir()

    kg = KnowledgeGraph()

    def fake_ensure_graphs(_repo: Path, _out_dir: Path) -> KnowledgeGraph:
        return kg

    monkeypatch.setattr(cli, "_ensure_graphs", fake_ensure_graphs)

    result = runner.invoke(
        cli.app,
        [
            "brief",
            str(repo),
            "--output-dir",
            str(output_dir),
            "--format",
            "json-summary",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert "primary_ingestion_path" in data
    assert "critical_datasets" in data
    assert "blast_radius" in data
    assert "business_logic_locations" in data
    assert "most_active_files" in data


def test_lineage_json_output(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    output_dir = tmp_path / ".cartography"
    output_dir.mkdir()

    kg = KnowledgeGraph()
    kg.lineage_graph.add_edge("source_dataset", "downstream_dataset")

    def fake_ensure_graphs(_repo: Path, _out_dir: Path) -> KnowledgeGraph:
        return kg

    monkeypatch.setattr(cli, "_ensure_graphs", fake_ensure_graphs)

    result = runner.invoke(
        cli.app,
        [
            "lineage",
            str(repo),
            "source_dataset",
            "--output-dir",
            str(output_dir),
            "--json",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["target"] == "source_dataset"
    assert data["upstream"] == []
    assert data["downstream"] == ["downstream_dataset"]


def test_map_json_output(monkeypatch, tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()
    output_dir = tmp_path / ".cartography"
    output_dir.mkdir()

    kg = KnowledgeGraph()
    kg.module_graph.add_edge("upstream_module", "downstream_module")

    def fake_ensure_graphs(_repo: Path, _out_dir: Path) -> KnowledgeGraph:
        return kg

    monkeypatch.setattr(cli, "_ensure_graphs", fake_ensure_graphs)

    result = runner.invoke(
        cli.app,
        [
            "map",
            str(repo),
            "upstream_module",
            "--output-dir",
            str(output_dir),
            "--json",
        ],
    )

    assert result.exit_code == 0
    data = json.loads(result.stdout)
    assert data["target"] == "upstream_module"
    assert data["upstream"] == []
    assert data["downstream"] == ["downstream_module"]

