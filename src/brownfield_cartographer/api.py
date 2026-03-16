from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
import threading
import time
import uuid
import tempfile
import shutil

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from starlette.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.exc import SQLAlchemyError

from .agents.semanticist import DayOneSemanticist
from .cli import _load_dotenv, _resolve_repo_path, _iter_env_paths, GITHUB_URL_PATTERN
from .db import Run, get_session, init_db
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
    provider: Optional[str] = None
    model: Optional[str] = None
    fallback_provider: Optional[str] = None
    fallback_model: Optional[str] = None
    api_key: Optional[str] = None
    fallback_api_key: Optional[str] = None
    base_url: Optional[str] = None
    quota_depleted: bool = False


class ChatResponse(BaseModel):
    answer: str
    hints: List[str]


class RunRequest(BaseModel):
    repo_path: str
    output_dir: str = ".cartography"
    run_lineage: bool = True
    run_semantic: bool = True
    ignore_globs: List[str] = Field(default_factory=list)


class RunResponse(BaseModel):
    run_id: str
    status: str
    repo_path: str
    output_dir: str
    started_at: str
    completed_at: Optional[str] = None
    error: Optional[str] = None


class RunListResponse(BaseModel):
    runs: List[RunResponse]


app = FastAPI(title="Brownfield Cartographer API")

allowed_origins = os.getenv("CARTOGRAPHY_UI_ORIGINS", "*").split(",")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[origin.strip() for origin in allowed_origins],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"]
)

RUNS: Dict[str, Dict[str, Any]] = {}
RUNS_LOCK = threading.Lock()


@app.on_event("startup")
def _startup() -> None:
    init_db()


def _now_iso() -> str:
    from datetime import datetime, timezone

    return datetime.now(timezone.utc).isoformat()


def _is_github_url(repo_path: str) -> bool:
    return GITHUB_URL_PATTERN.match(repo_path.strip()) is not None


def _is_temp_clone(original_repo: str, resolved_repo: Path) -> bool:
    if not _is_github_url(original_repo):
        return False
    temp_root = Path(tempfile.gettempdir()).resolve()
    try:
        resolved = resolved_repo.resolve()
    except Exception:
        return False
    return resolved.is_dir() and str(resolved).startswith(str(temp_root)) and resolved.name.startswith("cartography_repo_")

def _run_to_response(run: Run) -> RunResponse:
    return RunResponse(
        run_id=run.run_id,
        status=run.status,
        repo_path=run.repo_path,
        output_dir=run.output_dir,
        started_at=run.started_at.isoformat(),
        completed_at=run.completed_at.isoformat() if run.completed_at else None,
        error=run.error,
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


def _resolve_env_path() -> Path:
    candidates = _iter_env_paths(Path.cwd())
    for candidate in candidates:
        if candidate.exists():
            return candidate
    return Path.cwd() / ".env"


def _write_env_values(path: Path, updates: Dict[str, str]) -> None:
    lines: List[str] = []
    if path.exists():
        lines = path.read_text(encoding="utf-8").splitlines()

    seen: set[str] = set()
    new_lines: List[str] = []
    for line in lines:
        if not line or line.strip().startswith("#") or "=" not in line:
            new_lines.append(line)
            continue
        key = line.split("=", 1)[0].strip()
        if key in updates:
            new_lines.append(f"{key}={updates[key]}")
            seen.add(key)
        else:
            new_lines.append(line)

    for key, value in updates.items():
        if key not in seen:
            new_lines.append(f"{key}={value}")

    path.write_text("\n".join(new_lines) + "\n", encoding="utf-8")


class EnvUpdateRequest(BaseModel):
    values: Dict[str, str]


@app.post("/settings/env")
def update_env(request: EnvUpdateRequest) -> Dict[str, Any]:
    allowed_keys = {
        "CARTOGRAPHY_LLM_PROVIDER",
        "CARTOGRAPHY_LLM_MODEL",
        "CARTOGRAPHY_LLM_FALLBACK_PROVIDER",
        "CARTOGRAPHY_LLM_FALLBACK_MODEL",
        "CARTOGRAPHY_LLM_API_KEY",
        "CARTOGRAPHY_LLM_FALLBACK_API_KEY",
        "CARTOGRAPHY_LLM_BASE_URL",
        "OPENROUTER_API_KEY",
        "OPENROUTER_MODEL",
        "OPENROUTER_BASE_URL",
        "OLLAMA_MODEL",
        "OLLAMA_HOST",
    }
    filtered = {k: v for k, v in request.values.items() if k in allowed_keys and v is not None and v != ""}
    if not filtered:
        raise HTTPException(status_code=400, detail="No supported keys provided.")

    env_path = _resolve_env_path()
    _write_env_values(env_path, filtered)
    return {"status": "ok", "path": str(env_path), "keys": sorted(filtered.keys())}


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


def _run_analysis_job(run_id: str, request: RunRequest) -> None:
    _load_dotenv()
    temp_clone: Optional[Path] = None
    try:
        repo_path = _resolve_repo_path(request.repo_path)
        output_dir = _resolve_output_dir(request.output_dir)
        if _is_temp_clone(request.repo_path, repo_path):
            temp_clone = repo_path
        with RUNS_LOCK:
            RUNS[run_id]["repo_path"] = str(repo_path)
            RUNS[run_id]["output_dir"] = str(output_dir)
        with get_session() as session:
            run = session.get(Run, run_id)
            if run:
                run.repo_path = str(repo_path)
                run.output_dir = str(output_dir)
                session.commit()

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

        completed_at = _now_iso()
        updates = {"status": "complete", "completed_at": completed_at}
        with RUNS_LOCK:
            RUNS[run_id].update(updates)
        with get_session() as session:
            run = session.get(Run, run_id)
            if run:
                run.status = "complete"
                run.completed_at = datetime.fromisoformat(completed_at)
                session.commit()
    except Exception as exc:  # pragma: no cover - guard rail
        completed_at = _now_iso()
        updates = {"status": "failed", "completed_at": completed_at, "error": str(exc)}
        with RUNS_LOCK:
            RUNS[run_id].update(updates)
            output_dir = Path(RUNS[run_id].get("output_dir", ".cartography"))
        try:
            with get_session() as session:
                run = session.get(Run, run_id)
                if run:
                    run.status = "failed"
                    run.completed_at = datetime.fromisoformat(completed_at)
                    run.error = str(exc)
                    session.commit()
        except SQLAlchemyError:
            pass
    finally:
        if temp_clone and temp_clone.exists():
            shutil.rmtree(temp_clone, ignore_errors=True)


@app.post("/runs", response_model=RunResponse)
def start_run(request: RunRequest) -> RunResponse:
    output_dir = _resolve_output_dir(request.output_dir)
    run_id = uuid.uuid4().hex
    started_at = _now_iso()
    record = {
        "run_id": run_id,
        "status": "running",
        "repo_path": request.repo_path,
        "output_dir": str(output_dir),
        "started_at": started_at,
        "completed_at": None,
        "error": None,
    }
    with RUNS_LOCK:
        RUNS[run_id] = dict(record)
    try:
        with get_session() as session:
            session.add(
                Run(
                    run_id=run_id,
                    status="running",
                    repo_path=request.repo_path,
                    output_dir=str(output_dir),
                    started_at=datetime.fromisoformat(started_at),
                )
            )
            session.commit()
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"DB error: {exc}") from exc

    thread = threading.Thread(target=_run_analysis_job, args=(run_id, request), daemon=True)
    thread.start()
    return RunResponse(**record)


@app.get("/runs", response_model=RunListResponse)
def list_runs(output_dir: str = ".cartography") -> RunListResponse:
    output = _resolve_output_dir(output_dir)
    try:
        with get_session() as session:
            stmt = select(Run).where(Run.output_dir == str(output)).order_by(Run.started_at)
            runs = session.execute(stmt).scalars().all()
            return RunListResponse(runs=[_run_to_response(run) for run in runs])
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"DB error: {exc}") from exc


@app.get("/runs/{run_id}", response_model=RunResponse)
def get_run(run_id: str) -> RunResponse:
    with RUNS_LOCK:
        record = RUNS.get(run_id)
    if record:
        return RunResponse(**record)
    try:
        with get_session() as session:
            run = session.get(Run, run_id)
            if not run:
                raise HTTPException(status_code=404, detail="Run not found.")
            return _run_to_response(run)
    except SQLAlchemyError as exc:
        raise HTTPException(status_code=500, detail=f"DB error: {exc}") from exc


@app.get("/runs/{run_id}/events")
def stream_run_events(run_id: str) -> StreamingResponse:
    def event_stream():
        last_size = 0
        last_status = None
        while True:
            with RUNS_LOCK:
                record = RUNS.get(run_id)
            if not record:
                yield "event: status\ndata: {\"status\":\"unknown\"}\n\n"
                break

            status = record.get("status")
            output_dir = Path(record.get("output_dir", ".cartography"))
            trace_path = output_dir / "cartography_trace.jsonl"

            if status != last_status:
                last_status = status
                payload = json.dumps({"status": status, "run_id": run_id})
                yield f"event: status\ndata: {payload}\n\n"

            if trace_path.exists():
                current_size = trace_path.stat().st_size
                if current_size > last_size:
                    with trace_path.open("r", encoding="utf-8") as handle:
                        handle.seek(last_size)
                        for line in handle:
                            line = line.strip()
                            if not line:
                                continue
                            yield f"event: trace\ndata: {line}\n\n"
                    last_size = current_size

            if status in ("complete", "failed"):
                break

            time.sleep(1)

    return StreamingResponse(event_stream(), media_type="text/event-stream")


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


class LlmError(RuntimeError):
    def __init__(self, message: str, quota: bool = False) -> None:
        super().__init__(message)
        self.quota = quota


def _normalize_provider(provider: str | None) -> str:
    if not provider:
        return "ollama"
    return provider.strip().lower()


def _resolve_llm_config(request: ChatRequest) -> Tuple[str, str, str | None, str | None, str | None, str | None]:
    provider = request.provider or os.getenv("CARTOGRAPHY_LLM_PROVIDER") or "ollama"
    model = request.model or os.getenv("CARTOGRAPHY_LLM_MODEL") or os.getenv("OLLAMA_MODEL") or "llama3.1"
    fallback_provider = request.fallback_provider or os.getenv("CARTOGRAPHY_LLM_FALLBACK_PROVIDER") or "openrouter"
    fallback_model = request.fallback_model or os.getenv("CARTOGRAPHY_LLM_FALLBACK_MODEL") or os.getenv("OPENROUTER_MODEL")
    api_key = request.api_key or os.getenv("CARTOGRAPHY_LLM_API_KEY") or os.getenv("OPENROUTER_API_KEY")
    fallback_api_key = (
        request.fallback_api_key
        or os.getenv("CARTOGRAPHY_LLM_FALLBACK_API_KEY")
        or os.getenv("OPENROUTER_API_KEY")
    )
    return provider, model, fallback_provider, fallback_model, api_key, fallback_api_key


def _http_json(url: str, payload: Dict[str, Any], headers: Dict[str, str], timeout: int = 180) -> Dict[str, Any]:
    data = json.dumps(payload).encode("utf-8")
    req = urllib.request.Request(url, data=data, headers=headers, method="POST")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            raw = resp.read().decode("utf-8")
    except urllib.error.HTTPError as exc:
        body = exc.read().decode("utf-8") if exc.fp else ""
        quota = exc.code in (402, 429) or "quota" in body.lower()
        raise LlmError(body or f"HTTP {exc.code}", quota=quota) from exc
    except urllib.error.URLError as exc:
        raise LlmError(str(exc)) from exc
    return json.loads(raw)


def _call_ollama(prompt: str, model: str, base_url: str) -> str:
    payload = {"model": model, "prompt": prompt, "stream": False}
    data = _http_json(f"{base_url.rstrip('/')}/api/generate", payload, {"Content-Type": "application/json"}, timeout=60)
    return str(data.get("response", "")).strip()


def _call_openrouter(prompt: str, model: str, api_key: str, base_url: str) -> str:
    payload = {
        "model": model,
        "messages": [
            {"role": "system", "content": "You are a senior software engineer. Answer concisely."},
            {"role": "user", "content": prompt},
        ],
    }
    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json",
    }
    data = _http_json(f"{base_url.rstrip('/')}/chat/completions", payload, headers, timeout=180)
    return data["choices"][0]["message"]["content"].strip()


def _run_llm(provider: str, model: str, prompt: str, api_key: str | None, base_url: str | None) -> str:
    normalized = _normalize_provider(provider)
    if normalized == "ollama":
        base = base_url or os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        if not model:
            raise LlmError("OLLAMA_MODEL not set")
        return _call_ollama(prompt, model, base)

    # Route all non-ollama providers through OpenRouter for now.
    base = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
    key = api_key or os.getenv("OPENROUTER_API_KEY")
    if not key:
        raise LlmError("OPENROUTER_API_KEY not set for remote providers")
    if not model:
        raise LlmError("Model not set for remote providers")
    return _call_openrouter(prompt, model, key, base)


@app.post("/chat", response_model=ChatResponse)
def chat(request: ChatRequest) -> ChatResponse:
    _load_dotenv()
    output = _resolve_output_dir(request.output_dir)
    answers = day_one_insights(str(output))

    provider, model, fallback_provider, fallback_model, api_key, fallback_api_key = _resolve_llm_config(request)
    base_url = request.base_url or os.getenv("CARTOGRAPHY_LLM_BASE_URL") or os.getenv("OLLAMA_HOST")

    prompt = (
        "Use the following onboarding intelligence to answer the question.\n\n"
        f"Main ingestion path: {answers['main_ingestion_path']}\n"
        f"Critical datasets: {answers['critical_datasets']}\n"
        f"Blast radius: {answers['blast_radius']}\n"
        f"Business logic locations: {answers['business_logic_locations']}\n"
        f"Most active files: {answers['most_active_files']}\n\n"
        f"Question: {request.question}\n"
        "Answer in 2-4 concise sentences."
    )

    error: str | None = None
    response_text: str | None = None

    if not request.quota_depleted:
        try:
            response_text = _run_llm(provider, model, prompt, api_key, base_url)
        except LlmError as exc:
            error = str(exc)
            if not exc.quota:
                fallback_model = fallback_model or model
            response_text = None

    if response_text is None and fallback_provider and fallback_model:
        try:
            response_text = _run_llm(fallback_provider, fallback_model, prompt, fallback_api_key, base_url)
        except LlmError as exc:
            error = str(exc)
            response_text = None

    if response_text is None:
        response_text = " ".join(
            [
                answers["main_ingestion_path"],
                answers["critical_datasets"],
                answers["blast_radius"],
                answers["business_logic_locations"],
                answers["most_active_files"],
            ]
        )
        if error:
            response_text = f"{response_text}\n\n(LLM unavailable: {error})"

    hints = [
        "Ask about blast radius for a dataset",
        "Ask which modules contain business logic",
        "Ask which datasets are most critical",
    ]
    return ChatResponse(answer=response_text, hints=hints)


def run() -> None:
    import uvicorn

    host = os.getenv("CARTOGRAPHY_API_HOST", "0.0.0.0")
    port = int(os.getenv("CARTOGRAPHY_API_PORT", "8000"))
    uvicorn.run("brownfield_cartographer.api:app", host=host, port=port, reload=False)


if __name__ == "__main__":
    run()
