from __future__ import annotations

import json
import os
import re
import urllib.request
import urllib.error
from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional, Tuple

from .db import Document, get_session


def _default_embed_model() -> str:
    return os.getenv("CARTOGRAPHY_EMBED_MODEL", "nomic-embed-text")


def _ollama_base_url() -> str:
    return os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")


def _normalize_text(text: str) -> str:
    return text.replace("\r\n", "\n")


def _read_text(path: Path) -> str:
    return path.read_text(encoding="utf-8", errors="ignore")


def _is_binary(path: Path) -> bool:
    try:
        data = path.read_bytes()[:2048]
    except Exception:
        return True
    return b"\x00" in data


def _iter_files(repo_path: Path, ignore_globs: Iterable[str]) -> List[Path]:
    ignore = {p for p in ignore_globs}
    results: List[Path] = []
    for path in repo_path.rglob("*"):
        if path.is_dir():
            continue
        rel = str(path.relative_to(repo_path))
        if any(Path(rel).match(pattern) for pattern in ignore):
            continue
        if "/.git/" in rel or rel.startswith(".git/"):
            continue
        if rel.startswith(".venv/") or "/node_modules/" in rel:
            continue
        results.append(path)
    return results


def _chunk_text(text: str, max_chars: int = 1200, overlap: int = 200) -> List[str]:
    text = _normalize_text(text)
    if len(text) <= max_chars:
        return [text]
    chunks: List[str] = []
    start = 0
    while start < len(text):
        end = min(len(text), start + max_chars)
        chunk = text[start:end]
        chunks.append(chunk)
        if end == len(text):
            break
        start = max(0, end - overlap)
    return chunks


def _embed_batch(texts: List[str], model: str, base_url: str) -> List[List[float]]:
    embeddings: List[List[float]] = []
    for text in texts:
        payload = {"model": model, "prompt": text}
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{base_url.rstrip('/')}/api/embeddings",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        try:
            with urllib.request.urlopen(req, timeout=60) as resp:
                raw = resp.read().decode("utf-8")
            parsed = json.loads(raw)
            embeddings.append(parsed.get("embedding", []))
        except (urllib.error.URLError, urllib.error.HTTPError, json.JSONDecodeError):
            embeddings.append([])
    return embeddings


def index_repo(repo_path: Path, ignore_globs: Iterable[str] | None = None) -> int:
    ignore_globs = ignore_globs or []
    model = _default_embed_model()
    base_url = _ollama_base_url()

    files = _iter_files(repo_path, ignore_globs)
    indexed = 0
    with get_session() as session:
        for path in files:
            if _is_binary(path):
                continue
            try:
                text = _read_text(path)
            except Exception:
                continue
            chunks = _chunk_text(text)
            embeddings = _embed_batch(chunks, model, base_url)
            for idx, chunk in enumerate(chunks):
                embedding = embeddings[idx] if idx < len(embeddings) else []
                doc = Document(
                    repo_path=str(repo_path),
                    file_path=str(path),
                    chunk_index=idx,
                    content=chunk,
                    embedding=json.dumps(embedding),
                )
                session.add(doc)
                indexed += 1
        session.commit()
    return indexed


def _cosine(a: List[float], b: List[float]) -> float:
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(y * y for y in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


def search_repo(repo_path: Path, query: str, top_k: int = 6) -> List[Tuple[str, str]]:
    model = _default_embed_model()
    base_url = _ollama_base_url()
    query_embedding = _embed_batch([query], model, base_url)[0]

    results: List[Tuple[str, str, float]] = []
    with get_session() as session:
        docs = session.query(Document).filter(Document.repo_path == str(repo_path)).all()
        for doc in docs:
            try:
                embedding = json.loads(doc.embedding) if doc.embedding else []
            except json.JSONDecodeError:
                embedding = []
            score = _cosine(query_embedding, embedding) if embedding else 0.0
            results.append((doc.file_path, doc.content, score))

    # fallback to keyword relevance if embeddings are empty
    if not query_embedding:
        terms = {t for t in re.split(r"\W+", query.lower()) if t}
        rescored: List[Tuple[str, str, float]] = []
        for file_path, content, _ in results:
            text = content.lower()
            score = sum(text.count(term) for term in terms)
            rescored.append((file_path, content, float(score)))
        results = rescored

    results.sort(key=lambda item: item[2], reverse=True)
    return [(file_path, content) for file_path, content, _ in results[:top_k]]
