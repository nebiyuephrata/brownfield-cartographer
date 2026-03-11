from __future__ import annotations

from pathlib import Path
from typing import Any, Dict

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

