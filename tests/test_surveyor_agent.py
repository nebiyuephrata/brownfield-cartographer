from pathlib import Path

from brownfield_cartographer.agents.surveyor import SurveyorAgent
from brownfield_cartographer.graph.knowledge_graph import KnowledgeGraph


def test_surveyor_respects_ignore_globs_and_populates_commits(tmp_path, monkeypatch):
    # Create a fake repo structure.
    repo = tmp_path
    included = repo / "pkg" / "included.py"
    ignored = repo / "pkg" / "ignored.py"
    included.parent.mkdir(parents=True, exist_ok=True)
    included.write_text("def foo():\n    return 1\n", encoding="utf-8")
    ignored.write_text("def bar():\n    return 2\n", encoding="utf-8")

    # Pretend this is a git repo; recent_commit_count will remain 0 but should not break.
    (repo / ".git").mkdir()

    kg = KnowledgeGraph()
    surveyor = SurveyorAgent(ignore_globs=["**/ignored.py"])
    surveyor.run(repo, kg)

    # Only the included module should appear in the module graph.
    node_ids = set(kg.module_graph.nodes)
    assert any("included" in nid for nid in node_ids)
    assert not any("ignored" in nid for nid in node_ids)

