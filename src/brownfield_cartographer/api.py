from __future__ import annotations

import json
import os
import re
from pathlib import Path
from typing import Any, Dict, List

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agents.semanticist import DayOneSemanticist
from .cli import _load_dotenv, _resolve_repo_path
from .graph.knowledge_graph import KnowledgeGraph
from .orchestrator import Orchestrator


README_CANDIDATES = ["README.md", "README.rst", "README.txt", "README"]


class AnalyzeRequest(BaseModel):
    repo_path: str
    output_dir: str = ".cartography"
    run_lineage: bool = True
    run_semantic: bool = True
    ignore_globs: List[str] = Field(default_factory=list)


class AnalyzeResponse(BaseModel):
    status: str
    repo_path: str
    output_dir: str
    module_nodes: int
    module_edges: int
    lineage_nodes: int
    lineage_edges: int


class ProgressStep(BaseModel):
    id: str
    label: str
    progress: int


class ProgressResponse(BaseModel):
    steps: List[ProgressStep]
    overall: int
    last_event: str | None = None


class ChatRequest(BaseModel):
    question: str
    output_dir: str = ".cartography"


class ChatResponse(BaseModel):
    answer: str
    hints: List[str]


app = FastAPI(title="Brownfield Cartographer API")

allowed_origins = os.getenv("CARTOGRAPHY_UI_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)


def _resolve_output_dir(output_dir: str) -> Path:
    path = Path(output_dir).expanduser().resolve()
    path.mkdir(parents=True, exist_ok=True)
    return path


def _read_json(path: Path) -> Dict[str, Any]:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Missing file: {path}")
    try:
        return json.loads(path.read_text(encoding="utf-8"))
    except json.JSONDecodeError as exc:
        raise HTTPException(status_code=500, detail=f"Invalid JSON in {path}: {exc}") from exc


def _read_markdown(path: Path) -> str:
    if not path.exists():
        raise HTTPException(status_code=404, detail=f"Missing markdown: {path}")
    return path.read_text(encoding="utf-8")


def _find_readme(repo_path: Path) -> Path:
    for name in README_CANDIDATES:
        candidate = repo_path / name
        if candidate.exists():
            return candidate
    raise HTTPException(status_code=404, detail="README not found in repo root")


def _load_knowledge_graph(output_dir: Path) -> KnowledgeGraph:
    return KnowledgeGraph.load_from_paths(
        module_graph_path=output_dir / "module_graph.json",
        lineage_graph_path=output_dir / "lineage_graph.json",
    )


@app.get("/health")
def health() -> Dict[str, str]:
    return {"status": "ok"}


@app.post("/analyze", response_model=AnalyzeResponse)
def analyze(request: AnalyzeRequest) -> AnalyzeResponse:
    _load_dotenv()
    repo_path = _resolve_repo_path(request.repo_path)
    output_dir = _resolve_output_dir(request.output_dir)

    orchestrator = Orchestrator(
        repo_path=repo_path,
        output_dir=output_dir,
        run_hydrologist=request.run_lineage,
        enable_semanticist=request.run_semantic,
        ignore_globs=request.ignore_globs,
    )
    orchestrator.run_surveyor()
    if request.run_lineage:
        orchestrator.run_hydrologist()
    if request.run_semantic:
        orchestrator.run_semanticist()

    module_nodes = orchestrator.kg.module_graph.number_of_nodes()
    module_edges = orchestrator.kg.module_graph.number_of_edges()
    lineage_nodes = orchestrator.kg.lineage_graph.number_of_nodes()
    lineage_edges = orchestrator.kg.lineage_graph.number_of_edges()

    return AnalyzeResponse(
        status="complete",
        repo_path=str(repo_path),
        output_dir=str(output_dir),
        module_nodes=module_nodes,
        module_edges=module_edges,
        lineage_nodes=lineage_nodes,
        lineage_edges=lineage_edges,
    )


@app.get("/graphs/module")
def module_graph(output_dir: str = ".cartography") -> Dict[str, Any]:
    path = _resolve_output_dir(output_dir) / "module_graph.json"
    return _read_json(path)


@app.get("/graphs/lineage")
def lineage_graph(output_dir: str = ".cartography") -> Dict[str, Any]:
    path = _resolve_output_dir(output_dir) / "lineage_graph.json"
    return _read_json(path)


@app.get("/markdown/readme")
def markdown_readme(repo_path: str) -> Dict[str, str]:
    resolved = _resolve_repo_path(repo_path)
    readme_path = _find_readme(resolved)
    return {"content": _read_markdown(readme_path)}


@app.get("/markdown/onboarding")
def markdown_onboarding(output_dir: str = ".cartography") -> Dict[str, str]:
    output = _resolve_output_dir(output_dir)
    return {"content": _read_markdown(output / "ONBOARDING_BRIEF.md")}


@app.get("/progress", response_model=ProgressResponse)
def progress(output_dir: str = ".cartography") -> ProgressResponse:
    output = _resolve_output_dir(output_dir)
    trace_path = output / "cartography_trace.jsonl"
    steps = [
        ProgressStep(id="scan", label="Repository scan", progress=0),
        ProgressStep(id="deps", label="Module dependency graph", progress=0),
        ProgressStep(id="lineage", label="Lineage extraction", progress=0),
        ProgressStep(id="summaries", label="Semantic summaries", progress=0),
    ]
    last_event = None

    if trace_path.exists():
        for raw in trace_path.read_text(encoding="utf-8").splitlines():
            if not raw.strip():
                continue
            try:
                event = json.loads(raw)
            except json.JSONDecodeError:
                continue
            last_event = event.get("event")
            if event.get("event") == "surveyor_start":
                steps[0].progress = max(steps[0].progress, 35)
            if event.get("event") == "surveyor_complete":
                steps[0].progress = 100
                steps[1].progress = 100
            if event.get("event") == "hydrologist_start":
                steps[2].progress = max(steps[2].progress, 35)
            if event.get("event") == "hydrologist_complete":
                steps[2].progress = 100
            if event.get("event") == "semanticist_start":
                steps[3].progress = max(steps[3].progress, 35)
            if event.get("event") == "semanticist_complete":
                steps[3].progress = 100

    overall = int(sum(step.progress for step in steps) / len(steps))
    return ProgressResponse(steps=steps, overall=overall, last_event=last_event)


@app.get("/insights/day-one")
def day_one_insights(output_dir: str = ".cartography") -> Dict[str, str]:
    output = _resolve_output_dir(output_dir)
    kg = _load_knowledge_graph(output)
    semanticist = DayOneSemanticist()
    answers = semanticist.compute_day_one_answers(kg)
    return {
        "main_ingestion_path": answers.main_ingestion_path,
        "critical_datasets": answers.critical_datasets,
        "blast_radius": answers.blast_radius,
        "business_logic_locations": answers.business_logic_locations,
        "most_active_files": answers.most_active_files,
    }


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    output = _resolve_output_dir(request.output_dir)
    answers = day_one_insights(str(output))
    question = request.question.lower()

    key_map = {
        "blast": "blast_radius",
        "impact": "blast_radius",
        "ingestion": "main_ingestion_path",
        "critical": "critical_datasets",
        "logic": "business_logic_locations",
        "active": "most_active_files",
    }

    matched = None
    for token, key in key_map.items():
        if token in question:
            matched = key
            break

    if matched:
        answer = answers[matched]
    else:
        answer = " ".join(
            [
                answers["main_ingestion_path"],
                answers["critical_datasets"],
                answers["blast_radius"],
                answers["business_logic_locations"],
                answers["most_active_files"],
            ]
        )

    hints = [
        "Ask about blast radius for a dataset",
        "Ask which modules contain business logic",
        "Ask which datasets are most critical",
    ]
    return ChatResponse(answer=answer, hints=hints)


def run() -> None:
    import uvicorn

    host = os.getenv("CARTOGRAPHY_API_HOST", "0.0.0.0")
    port = int(os.getenv("CARTOGRAPHY_API_PORT", "8000"))
    uvicorn.run("brownfield_cartographer.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()
