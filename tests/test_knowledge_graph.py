from pathlib import Path

from brownfield_cartographer.graph.knowledge_graph import KnowledgeGraph
from brownfield_cartographer.models.edges import LineageEdge, ModuleDependencyEdge
from brownfield_cartographer.models.nodes import DatasetNode, Evidence, ModuleNode


def test_knowledge_graph_module_and_lineage_round_trip(tmp_path):
    kg = KnowledgeGraph()

    evidence = Evidence(
        file_path="tests/sample.py",
        line_start=1,
        line_end=10,
        method="test",
    )

    module_node = ModuleNode(
        id="pkg.sample",
        path="pkg/sample.py",
        language="python",
        imports=["pkg.other"],
        functions=["foo"],
        classes=["Bar"],
        evidence=[evidence],
    )
    kg.add_module_node(module_node)

    module_edge = ModuleDependencyEdge(
        id="pkg.sample->pkg.other",
        source_module_id="pkg.sample",
        target_module_id="pkg.other",
        reason="import",
        evidence=[evidence],
    )
    kg.add_module_edge(module_edge)

    dataset_upstream = DatasetNode(
        id="table:raw_orders",
        name="raw_orders",
        type="source",
        evidence=[evidence],
    )
    dataset_downstream = DatasetNode(
        id="model:fct_orders",
        name="fct_orders",
        type="mart",
        evidence=[evidence],
    )
    kg.add_dataset_node(dataset_upstream)
    kg.add_dataset_node(dataset_downstream)

    lineage_edge = LineageEdge(
        id="table:raw_orders->model:fct_orders",
        source_dataset_id="table:raw_orders",
        target_dataset_id="model:fct_orders",
        transformation_id=None,
        evidence=[evidence],
    )
    kg.add_lineage_edge(lineage_edge)

    module_path = tmp_path / "module_graph.json"
    lineage_path = tmp_path / "lineage_graph.json"

    kg.save_module_graph(module_path)
    kg.save_lineage_graph(lineage_path)

    # Basic shape checks on saved JSON.
    module_payload = module_path.read_text(encoding="utf-8")
    lineage_payload = lineage_path.read_text(encoding="utf-8")

    assert "schema_version" in module_payload
    assert "nodes" in module_payload
    assert "edges" in module_payload

    assert "schema_version" in lineage_payload
    assert "nodes" in lineage_payload
    assert "edges" in lineage_payload

