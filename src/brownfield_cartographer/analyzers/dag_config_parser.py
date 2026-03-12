from __future__ import annotations

from pathlib import Path
from typing import Any, Dict, List, Optional

import yaml


def parse_dbt_project_config(path: Path) -> Dict[str, Any]:
    """
    Minimal parser for dbt_project.yml and model config YAMLs.

    This is intentionally light-weight and may be expanded later to
    enrich DatasetNode metadata.
    """
    try:
        text = path.read_text(encoding="utf-8", errors="ignore")
        return yaml.safe_load(text) or {}
    except FileNotFoundError:
        return {}
    except yaml.YAMLError:
        return {}


def extract_model_metadata(model_yaml: Dict[str, Any]) -> Dict[str, Any]:
    """
    Extract a small, normalized set of fields (tags, materialization, meta)
    from a dbt model YAML dictionary for DatasetNode.metadata.
    """
    result: Dict[str, Any] = {}
    if "tags" in model_yaml:
        result["tags"] = list(model_yaml.get("tags") or [])

    config = model_yaml.get("config") or {}
    materialized = config.get("materialized")
    if materialized:
        result["materialized"] = materialized

    meta = model_yaml.get("meta") or {}
    if meta:
        result["meta"] = meta

    return result


def extract_source_definitions(sources_yaml: Dict[str, Any]) -> List[Dict[str, Optional[str]]]:
    """
    Extract a flat list of dbt `source` table definitions suitable for enriching
    DatasetNode metadata.
    """
    sources = []
    for source in sources_yaml.get("sources", []) or []:
        name = source.get("name")
        schema = source.get("schema")
        for table in source.get("tables", []) or []:
            sources.append(
                {
                    "source_name": name,
                    "table_name": table.get("name"),
                    "schema": schema,
                    "identifier": table.get("identifier"),
                }
            )
    return sources

