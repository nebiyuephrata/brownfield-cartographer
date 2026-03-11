from pathlib import Path

import pytest

from brownfield_cartographer.orchestrator import Orchestrator


@pytest.mark.integration
def test_e2e_analyze_jaffle_shop(tmp_path):
    """
    End-to-end smoke test against jaffle_shop if it is available locally.

    To run this test, set the JAFFLE_SHOP_PATH environment variable to the
    path of a cloned https://github.com/dbt-labs/jaffle_shop repository.
    If the variable is not set or the path does not exist, the test is
    skipped.
    """
    jaffle_env = "JAFFLE_SHOP_PATH"
    jaffle_path_str = os.getenv(jaffle_env)
    if not jaffle_path_str:
        pytest.skip(f"{jaffle_env} not set; skipping e2e test")

    repo_path = Path(jaffle_path_str).expanduser().resolve()
    if not repo_path.exists():
        pytest.skip(f"{repo_path} does not exist; skipping e2e test")

    output_dir = tmp_path / ".cartography"

    orchestrator = Orchestrator(repo_path=repo_path, output_dir=output_dir, output_format="json")
    orchestrator.run_all()

    module_graph_path = output_dir / "module_graph.json"
    lineage_graph_path = output_dir / "lineage_graph.json"

    assert module_graph_path.exists(), "Expected module_graph.json to be created"
    assert lineage_graph_path.exists(), "Expected lineage_graph.json to be created"

    # Files should not be empty.
    assert module_graph_path.read_text(encoding="utf-8").strip()
    assert lineage_graph_path.read_text(encoding="utf-8").strip()

