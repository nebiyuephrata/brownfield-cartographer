from __future__ import annotations

import json
import os
import urllib.error
import urllib.request
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field

from .agents.semanticist import DayOneSemanticist
from .cli import _load_dotenv, _resolve_repo_path, _iter_env_paths
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
