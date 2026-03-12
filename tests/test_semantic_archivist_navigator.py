from brownfield_cartographer.agents.archivist import ArchivistAgent
from brownfield_cartographer.agents.navigator import NavigatorAgent
from brownfield_cartographer.agents.semanticist import DayOneSemanticist
from brownfield_cartographer.graph.knowledge_graph import KnowledgeGraph
from brownfield_cartographer.models.edges import LineageEdge
from brownfield_cartographer.models.nodes import DatasetNode, Evidence, ModuleNode
from pathlib import Path


def _build_simple_graph(tmp_path):
    kg = KnowledgeGraph()
    ev = Evidence(file_path="x.py", line_start=1, line_end=1, method="test")

    module = ModuleNode(
        id="pkg.mod",
        path="pkg/mod.py",
        language="python",
        imports=[],
        functions=["f"],
        classes=[],
        evidence=[ev],
        metadata={"recent_commit_count": 3},
    )
    kg.add_module_node(module)

    upstream = DatasetNode(id="table:raw", name="raw", type="source", evidence=[ev])
    downstream = DatasetNode(id="model:stg", name="stg", type="mart", evidence=[ev])
    kg.add_dataset_node(upstream)
    kg.add_dataset_node(downstream)
    edge = LineageEdge(
        id="table:raw->model:stg",
        source_dataset_id="table:raw",
        target_dataset_id="model:stg",
        evidence=[ev],
    )
    kg.add_lineage_edge(edge)
    return kg


def test_day_one_semanticist_and_archivist(tmp_path):
    kg = _build_simple_graph(tmp_path)
    semanticist = DayOneSemanticist()
    answers = semanticist.compute_day_one_answers(kg)

    assert "Initial ingestion appears to start from" in answers.main_ingestion_path

    archivist = ArchivistAgent(repo_path=tmp_path, output_dir=tmp_path)
    codebase_path, onboarding_path, recon_path = archivist.write_codebase_docs(kg, semantic_answers=answers)

    assert codebase_path.exists()
    assert onboarding_path.exists()
    assert recon_path.exists()


def test_navigator_multi_hop_and_mart_filter(tmp_path):
    kg = _build_simple_graph(tmp_path)
    nav = NavigatorAgent(kg)

    upstream = nav.all_upstream_datasets("model:stg")
    assert "table:raw" in upstream

    mart_downstream = nav.mart_downstream_datasets("table:raw")
    assert "model:stg" in mart_downstream

