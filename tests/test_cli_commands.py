from pathlib import Path

from typer.testing import CliRunner

from brownfield_cartographer.cli import app


runner = CliRunner()


def test_cli_analyze_and_brief_help():
    result = runner.invoke(app, ["--help"])
    assert result.exit_code == 0
    assert "analyze" in result.stdout
    assert "brief" in result.stdout


def test_cli_lineage_and_map_commands_exist():
    result = runner.invoke(app, ["lineage", "--help"])
    assert result.exit_code == 0
    assert "dataset_id" in result.stdout

    result = runner.invoke(app, ["map", "--help"])
    assert result.exit_code == 0
    assert "module_id" in result.stdout


