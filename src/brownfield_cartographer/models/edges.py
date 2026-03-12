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


class DagDependencyEdge(BaseModel):
    """
    Edge between orchestration tasks (e.g., Airflow or other schedulers).
    """

    id: str
    upstream_task_id: str
    downstream_task_id: str
    evidence: List[Evidence] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModuleOwnershipEdge(BaseModel):
    """
    Edge connecting a module to a dataset it is primarily responsible for.
    """

    id: str
    module_id: str
    dataset_id: str
    evidence: List[Evidence] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class SimilarityEdge(BaseModel):
    """
    Edge capturing semantic or structural similarity between nodes.
    """

    id: str
    source_id: str
    target_id: str
    score: float = 0.0
    evidence: List[Evidence] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

