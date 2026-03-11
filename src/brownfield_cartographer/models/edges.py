from __future__ import annotations

from typing import Any, Dict, List

from pydantic import BaseModel, Field

from .nodes import Evidence


class ModuleDependencyEdge(BaseModel):
    id: str
    source_module_id: str
    target_module_id: str
    reason: str = "import"
    evidence: List[Evidence] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class LineageEdge(BaseModel):
    id: str
    source_dataset_id: str
    target_dataset_id: str
    transformation_id: str | None = None
    evidence: List[Evidence] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

