from __future__ import annotations

from dataclasses import dataclass
from typing import Dict, List, Protocol, runtime_checkable
import json
import os
import urllib.request
import urllib.error

import networkx as nx

from ..graph.knowledge_graph import KnowledgeGraph


@dataclass
class NodeSummary:
    """Lightweight container for semantic summaries."""

    id: str
    kind: str
    summary: str


class SemanticistAgent:
    """
    Semantic analysis agent.

    This implementation is intentionally LLM-agnostic. It produces simple,
    structured summaries from the existing graphs and stores them in the
    node metadata under a `semantic_summary` key so that an external LLM
    client can later refine or replace them.
    """

    def __init__(self) -> None:
        self.openrouter_api_key = os.getenv("OPENROUTER_API_KEY")
        self.openrouter_model = os.getenv("OPENROUTER_MODEL")
        self.openrouter_base_url = os.getenv("OPENROUTER_BASE_URL", "https://openrouter.ai/api/v1")
        self.ollama_model = os.getenv("OLLAMA_MODEL")
        self.ollama_base_url = os.getenv("OLLAMA_HOST", "http://127.0.0.1:11434")
        try:
            self.ollama_timeout = int(os.getenv("OLLAMA_TIMEOUT", "180"))
        except ValueError:
            self.ollama_timeout = 180
        try:
            self.max_items = int(os.getenv("SEMANTIC_MAX_ITEMS", "200"))
        except ValueError:
            self.max_items = 200

    def _openrouter_chat(self, prompt: str) -> str:
        if not self.openrouter_api_key or not self.openrouter_model:
            raise RuntimeError("OPENROUTER_API_KEY/OPENROUTER_MODEL not set")

        payload = {
            "model": self.openrouter_model,
            "messages": [
                {"role": "system", "content": "You are a senior software engineer. Answer concisely."},
                {"role": "user", "content": prompt},
            ],
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.openrouter_base_url}/chat/completions",
            data=data,
            headers={
                "Authorization": f"Bearer {self.openrouter_api_key}",
                "Content-Type": "application/json",
            },
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=self.ollama_timeout) as resp:
            raw = resp.read().decode("utf-8")
        parsed = json.loads(raw)
        return parsed["choices"][0]["message"]["content"].strip()

    def _ollama_generate(self, prompt: str) -> str:
        if not self.ollama_model:
            raise RuntimeError("OLLAMA_MODEL not set")
        payload = {
            "model": self.ollama_model,
            "prompt": prompt,
            "stream": False,
        }
        data = json.dumps(payload).encode("utf-8")
        req = urllib.request.Request(
            f"{self.ollama_base_url}/api/generate",
            data=data,
            headers={"Content-Type": "application/json"},
            method="POST",
        )
        with urllib.request.urlopen(req, timeout=60) as resp:
            raw = resp.read().decode("utf-8")
        parsed = json.loads(raw)
        return parsed.get("response", "").strip()

    def _llm_module_summary(self, node_id: str, attrs: Dict) -> str:
        functions = attrs.get("functions", [])[:20]
        classes = attrs.get("classes", [])[:20]
        imports = attrs.get("imports", [])[:20]
        prompt = (
            "Summarize the purpose of this module based on code structure only. "
            "Ignore docstrings and comments. Be specific, 1-2 sentences.\n\n"
            f"Module: {node_id}\n"
            f"Functions: {functions}\n"
            f"Classes: {classes}\n"
            f"Imports: {imports}\n"
        )
        if self.ollama_model:
            return self._ollama_generate(prompt)
        return self._openrouter_chat(prompt)

    def _llm_dataset_summary(self, node_id: str, attrs: Dict, upstream: List[str], downstream: List[str]) -> str:
        prompt = (
            "Summarize this dataset’s role in the lineage graph in 1-2 sentences. "
            "Focus on data flow and dependencies.\n\n"
            f"Dataset: {attrs.get('name', node_id)}\n"
            f"Type: {attrs.get('type', 'unknown')}\n"
            f"Upstream: {upstream[:20]}\n"
            f"Downstream: {downstream[:20]}\n"
        )
        if self.ollama_model:
            return self._ollama_generate(prompt)
        return self._openrouter_chat(prompt)

    def summarize_modules(self, kg: KnowledgeGraph) -> Dict[str, NodeSummary]:
        summaries: Dict[str, NodeSummary] = {}
        g = kg.module_graph

        for idx, (node_id, attrs) in enumerate(g.nodes(data=True)):
            if idx >= self.max_items:
                break
            imports: List[str] = attrs.get("imports", [])
            functions: List[str] = attrs.get("functions", [])
            classes: List[str] = attrs.get("classes", [])

            try:
                if self.ollama_model or (self.openrouter_api_key and self.openrouter_model):
                    text = self._llm_module_summary(node_id, attrs)
                else:
                    text = (
                        f"Module `{node_id}` defines "
                        f"{len(functions)} functions and {len(classes)} classes, "
                        f"and imports {len(imports)} modules."
                    )
            except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError, KeyError, ValueError, TimeoutError):
                text = (
                    f"Module `{node_id}` defines "
                    f"{len(functions)} functions and {len(classes)} classes, "
                    f"and imports {len(imports)} modules."
                )

            summaries[node_id] = NodeSummary(id=node_id, kind="module", summary=text)

            metadata = attrs.get("metadata") or {}
            metadata["semantic_summary"] = text
            if self.ollama_model:
                metadata["semantic_provider"] = "ollama"
            elif self.openrouter_api_key and self.openrouter_model:
                metadata["semantic_provider"] = "openrouter"
            else:
                metadata["semantic_provider"] = "heuristic"
            g.nodes[node_id]["metadata"] = metadata

        return summaries

    def summarize_datasets(self, kg: KnowledgeGraph) -> Dict[str, NodeSummary]:
        summaries: Dict[str, NodeSummary] = {}
        g = kg.lineage_graph

        for idx, (node_id, attrs) in enumerate(g.nodes(data=True)):
            if idx >= self.max_items:
                break
            node_type = attrs.get("type", "unknown")

            upstream = list(g.predecessors(node_id))
            downstream = list(g.successors(node_id))

            try:
                if self.ollama_model or (self.openrouter_api_key and self.openrouter_model):
                    text = self._llm_dataset_summary(node_id, attrs, upstream, downstream)
                else:
                    text = (
                        f"Dataset `{attrs.get('name', node_id)}` "
                        f"(type={node_type}) has {len(upstream)} upstream "
                        f"and {len(downstream)} downstream dependencies."
                    )
            except (urllib.error.URLError, urllib.error.HTTPError, RuntimeError, KeyError, ValueError, TimeoutError):
                text = (
                    f"Dataset `{attrs.get('name', node_id)}` "
                    f"(type={node_type}) has {len(upstream)} upstream "
                    f"and {len(downstream)} downstream dependencies."
                )

            summaries[node_id] = NodeSummary(id=node_id, kind="dataset", summary=text)

            metadata = attrs.get("metadata") or {}
            metadata["semantic_summary"] = text
            if self.ollama_model:
                metadata["semantic_provider"] = "ollama"
            elif self.openrouter_api_key and self.openrouter_model:
                metadata["semantic_provider"] = "openrouter"
            else:
                metadata["semantic_provider"] = "heuristic"
            g.nodes[node_id]["metadata"] = metadata

        return summaries

    def run(self, kg: KnowledgeGraph) -> Dict[str, Dict[str, NodeSummary]]:
        """
        Populate basic semantic summaries on module and dataset nodes.
        """
        module_summaries = self.summarize_modules(kg)
        dataset_summaries = self.summarize_datasets(kg)
        return {
            "modules": module_summaries,
            "datasets": dataset_summaries,
        }


@runtime_checkable
class LLMClient(Protocol):
    """
    Protocol for an external LLM client that can be used to refine or replace
    the deterministic summaries produced by SemanticistAgent.
    """

    def summarize(self, prompt: str) -> str:  # pragma: no cover - interface only
        ...


@dataclass
class DayOneAnswers:
    main_ingestion_path: str
    critical_datasets: str
    blast_radius: str
    business_logic_locations: str
    most_active_files: str


class DayOneSemanticist(SemanticistAgent):
    """
    Extension of SemanticistAgent that computes structured answers aligned with
    the five Day-One onboarding questions.
    """

    def compute_day_one_answers(self, kg: KnowledgeGraph) -> DayOneAnswers:
        # Reuse simple heuristics based on graph structure and semantic summaries.
        lineage = kg.lineage_graph
        modules = kg.module_graph

        # 1. Main ingestion path (source nodes with outgoing edges).
        if lineage.number_of_nodes() == 0:
            main_ingestion = "No lineage graph detected; run `cartography analyze` first."
        else:
            sources = [n for n in lineage.nodes if lineage.in_degree(n) == 0 and lineage.out_degree(n) > 0]
            if sources:
                names = ", ".join(sorted(lineage.nodes[s].get("name", s) for s in sources))
                main_ingestion = f"Initial ingestion appears to start from: {names}."
            else:
                main_ingestion = "No clear source datasets found in the lineage graph."

        # 2. Critical datasets by downstream fan-out.
        if lineage.number_of_nodes() == 0:
            critical = "No datasets discovered yet."
        else:
            by_out_degree = sorted(lineage.nodes, key=lambda n: lineage.out_degree(n), reverse=True)[:5]
            if by_out_degree:
                parts = [
                    f"{lineage.nodes[n].get('name', n)} (downstream count={lineage.out_degree(n)})"
                    for n in by_out_degree
                ]
                critical = "Top critical datasets by downstream fan-out: " + ", ".join(parts) + "."
            else:
                critical = "No downstream dependencies found."

        # 3. Blast radius via max descendants.
        if lineage.number_of_nodes() == 0:
            blast = "Blast radius cannot be computed without a lineage graph."
        else:
            best_node = None
            best_reach = -1
            for node in lineage.nodes:
                reach = len(nx.descendants(lineage, node))
                if reach > best_reach:
                    best_reach = reach
                    best_node = node
            if best_node is None or best_reach <= 0:
                blast = "No meaningful blast radius identified; graph may be sparse."
            else:
                name = lineage.nodes[best_node].get("name", best_node)
                blast = (
                    f"If `{name}` fails, up to {best_reach} downstream datasets could be impacted "
                    "according to the lineage graph."
                )

        # 4. Business logic locations via high function/class/import counts.
        if modules.number_of_nodes() == 0:
            logic = "No modules discovered yet."
        else:
            def score(node_id: str) -> int:
                attrs = modules.nodes[node_id]
                return (
                    len(attrs.get("functions", []))
                    + len(attrs.get("classes", []))
                    + len(attrs.get("imports", []))
                )

            ranked = sorted(modules.nodes, key=score, reverse=True)[:5]
            parts = []
            for nid in ranked:
                attrs = modules.nodes[nid]
                parts.append(
                    f"{nid} (functions={len(attrs.get('functions', []))}, "
                    f"classes={len(attrs.get('classes', []))}, imports={len(attrs.get('imports', []))})"
                )
            logic = "Likely business-logic-heavy modules: " + ", ".join(parts) + "."

        # 5. Most active files from recent_commit_count metadata.
        if modules.number_of_nodes() == 0:
            active = "No modules discovered yet."
        else:
            modules_with_activity: List[tuple[str, int]] = []
            for node_id, attrs in modules.nodes(data=True):
                metadata = attrs.get("metadata") or {}
                commit_count = int(metadata.get("recent_commit_count", 0))
                modules_with_activity.append((node_id, commit_count))
            modules_with_activity.sort(key=lambda x: x[1], reverse=True)
            top = [m for m in modules_with_activity if m[1] > 0][:5]
            if not top:
                active = "No git activity metadata found; run in a git repo for change velocity signals."
            else:
                parts = [f"{m} ({c} commits in recent window)" for m, c in top]
                active = "Most active modules by recent git commits: " + ", ".join(parts) + "."

        return DayOneAnswers(
            main_ingestion_path=main_ingestion,
            critical_datasets=critical,
            blast_radius=blast,
            business_logic_locations=logic,
            most_active_files=active,
        )
