from pathlib import Path

from brownfield_cartographer.analyzers.sql_lineage import extract_lineage_from_sql


def test_extract_lineage_from_sql_basic(tmp_path):
    sql = """
    with source as (
        select * from raw_orders
    )
    select
        s.*,
        c.customer_name
    from source s
    join stg_customers c on s.customer_id = c.id
    """

    sql_path = tmp_path / "fct_orders.sql"
    sql_path.write_text(sql, encoding="utf-8")

    nodes, edges = extract_lineage_from_sql(sql_path)

    node_ids = {n.id for n in nodes}
    # Downstream dataset should be derived from file stem.
    assert "model:fct_orders" in node_ids

    # Upstream datasets should include table references.
    assert "table:raw_orders" in node_ids
    assert "table:stg_customers" in node_ids

    # We expect lineage edges from upstream -> downstream.
    edge_pairs = {(e.source_dataset_id, e.target_dataset_id) for e in edges}
    assert ("table:raw_orders", "model:fct_orders") in edge_pairs
    assert ("table:stg_customers", "model:fct_orders") in edge_pairs

