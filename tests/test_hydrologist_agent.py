from pathlib import Path

from brownfield_cartographer.agents.hydrologist import HydrologistAgent
from brownfield_cartographer.graph.knowledge_graph import KnowledgeGraph


def test_hydrologist_populates_datasets_and_transformations(tmp_path):
    repo = tmp_path
    sql_dir = repo / "models"
    sql_dir.mkdir(parents=True, exist_ok=True)

    sql_path = sql_dir / "fct_orders.sql"
    sql_path.write_text(
        """
        select * from raw_orders;
        """,
        encoding="utf-8",
    )

    kg = KnowledgeGraph()
    hydrologist = HydrologistAgent()
    hydrologist.run(repo, kg)

    # Dataset nodes should include a model and its upstream table.
    dataset_ids = set(kg.lineage_graph.nodes)
    assert "model:fct_orders" in dataset_ids
    assert "table:raw_orders" in dataset_ids

    # A transformation node should be present and referenced by edges.
    transformation_ids = {
        nid for nid, attrs in kg.lineage_graph.nodes(data=True) if attrs.get("kind") == "sql_model"
    }
    assert transformation_ids, "Expected at least one TransformationNode for the SQL model"

    edge_transforms = {data.get("transformation_id") for _, _, data in kg.lineage_graph.edges(data=True)}
    assert edge_transforms & transformation_ids

