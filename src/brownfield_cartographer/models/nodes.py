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


class DatasetNode(BaseModel):
    id: str
    name: str
    type: Literal["source", "staging", "mart", "unknown"] = "unknown"
    schema: Optional[str] = None
    evidence: List[Evidence] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)


class TransformationNode(BaseModel):
    id: str
    name: str
    kind: str = "sql_model"
    evidence: List[Evidence] = Field(default_factory=list)
    metadata: Dict[str, Any] = Field(default_factory=dict)

