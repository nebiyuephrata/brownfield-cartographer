from __future__ import annotations

from typing import Any, Dict, List, Literal, Optional

from pydantic import BaseModel, Field


class Evidence(BaseModel):
    file_path: str
    line_start: int
    line_end: int
    method: str
    metadata: Dict[str, Any] = Field(default_factory=dict)


class ModuleNode(BaseModel):
    id: str
    path: str
    language: str = "python"
    imports: List[str] = Field(default_factory=list)
    functions: List[str] = Field(default_factory=list)
    classes: List[str] = Field(default_factory=list)
    evidence: List[Evidence] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # Analytical metadata, kept as first-class fields so downstream
    # agents can rely on a stable schema instead of ad-hoc metadata keys.
    change_velocity_30d: float = 0.0
    is_dead_code_candidate: bool = False
    purpose_statement: Optional[str] = None
    domain_cluster: Optional[str] = None


class DatasetNode(BaseModel):
    id: str
    name: str
    type: Literal["source", "staging", "mart", "unknown"] = "unknown"
    schema: Optional[str] = None
    evidence: List[Evidence] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)
    # Analytical metadata parallel to ModuleNode so that lineage- and
    # blast-radius-focused agents have a consistent surface area.
    change_velocity_30d: float = 0.0
    is_dead_code_candidate: bool = False
    purpose_statement: Optional[str] = None
    domain_cluster: Optional[str] = None


class TransformationNode(BaseModel):
    id: str
    name: str
    kind: str = "sql_model"
    evidence: List[Evidence] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class DagNode(BaseModel):
    """
    Lightweight representation of an orchestration or scheduler task.

    This gives the knowledge graph a fourth explicit node type so that
    pipeline-level dependencies can be attached alongside modules,
    datasets, and transformations when available.
    """

    id: str
    name: str
    dag_name: Optional[str] = None
    evidence: List[Evidence] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

