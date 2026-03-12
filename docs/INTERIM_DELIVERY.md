# TRP 1 Week 4 — Interim Delivery: The Brownfield Cartographer

**Deadline: Thursday March 12, 03:00 UTC**

This document is the required **Single PDF Report** content for the interim delivery, per the challenge in `ref/TRP 1 Challenge Week 4_ The Brownfield Cartographer.docx`.

---

## Feedback: “Are these still missing?”

Review feedback stated: *“Advanced analytics (Surveyor metrics), multi-source lineage merging and queries (Hydrologist), richer multi-language parsing, and some schema completeness are missing.”* Status as of this delivery:

| Feedback item | Status | Details |
|---------------|--------|---------|
| **Advanced analytics (Surveyor metrics)** | **Implemented** | Surveyor runs **PageRank**, **git velocity** (configurable window, e.g. 30d), **dead-code candidates** (exported symbols with no importers), and **circular dependency detection** (strongly connected components). Results are attached to module nodes (`pagerank`, `change_velocity_30d`, `is_dead_code_candidate`, `in_cycle`, `cycle_members`). |
| **Multi-source lineage merging and queries (Hydrologist)** | **Partially** | **Merging:** SQL lineage (sqlglot) + dbt YAML (model metadata, source definitions) are merged into one lineage graph. **Queries:** `blast_radius(kg, dataset_id)`, `find_sources(kg, dataset_id)`, `find_sinks(kg, dataset_id)` are implemented. **Still missing:** Python data-flow lineage (pandas read/write, SQLAlchemy, PySpark), Airflow DAG → lineage edges, notebook (.ipynb) source/sink extraction. |
| **Richer multi-language parsing** | **Partially** | **Python:** Full tree-sitter AST (or heuristic fallback) for imports, functions, classes. **Router:** `analyze_module(path)` dispatches by extension (`.py` → Python). **Still missing:** JavaScript/TypeScript AST, YAML AST for structural parsing; SQL/YAML currently have placeholders or are handled only in sql_lineage/dag_config, not as “module” AST. |
| **Schema completeness** | **Implemented** | Four node types (Module, Dataset, Transformation, Dag) and five edge types (ModuleDependency, Lineage, DagDependency, ModuleOwnership, Similarity) with analytical fields (`change_velocity_30d`, `is_dead_code_candidate`, `purpose_statement`, `domain_cluster`) and sensible defaults. Optional: add Pydantic field validators for stricter validation. |

**Summary:** Surveyor metrics and schema completeness are in place. Hydrologist has unified lineage from SQL + dbt and the three query helpers; adding Python/Airflow/notebook sources would make it “full” multi-source. Multi-language is in place for Python with a clear extension point; adding JS/TS/YAML AST would make it “richer.”

---

## 1. Deliverables Checklist (from ref challenge)

**Path mapping:** The assignment says `src/…`. This repo uses a package layout: **`src/brownfield_cartographer/…`**. So `src/cli.py` → `src/brownfield_cartographer/cli.py`, etc. All required behaviour lives under `src/brownfield_cartographer/`.

### 1.1 GitHub code (required paths) — verified in codebase

| Required (assignment) | Actual path in repo | In codebase? | Evidence |
|------------------------|----------------------|--------------|----------|
| `src/cli.py` — entry point, repo path (local or GitHub URL), runs analysis | `src/brownfield_cartographer/cli.py` | ✓ Yes | `_resolve_repo_path()` accepts local path or GitHub URL (clone); `@app.command()` `analyze(repo_path, ...)` runs analysis; `cartography` script in pyproject points here. |
| `src/orchestrator.py` — wires Surveyor + Hydrologist, serializes to .cartography/ | `src/brownfield_cartographer/orchestrator.py` | ✓ Yes | `run_surveyor()` then `run_hydrologist()` (and `run_semanticist()`); `save_module_graph()` / `save_lineage_graph()` to `output_dir` (default .cartography/). |
| `src/models/` — Pydantic schemas (Node, Edge, Graph types) | `src/brownfield_cartographer/models/` | ✓ Yes | `nodes.py`: ModuleNode, DatasetNode, TransformationNode, DagNode, Evidence; `edges.py`: ModuleDependencyEdge, LineageEdge, DagDependencyEdge, ModuleOwnershipEdge, SimilarityEdge. |
| `src/analyzers/tree_sitter_analyzer.py` — multi-language AST, LanguageRouter | `src/brownfield_cartographer/analyzers/tree_sitter_analyzer.py` | ✓ Yes | `analyze_python_module()` (tree-sitter AST or heuristic); `analyze_module(path)` routes by extension (`.py` → Python). |
| `src/analyzers/sql_lineage.py` — sqlglot SQL dependency extraction | `src/brownfield_cartographer/analyzers/sql_lineage.py` | ✓ Yes | `extract_lineage_from_sql()` uses sqlglot; FROM/JOIN/CTE; dbt `ref()`; multi-dialect; returns DatasetNodes + LineageEdges. |
| `src/analyzers/dag_config_parser.py` — Airflow/dbt YAML parsing | `src/brownfield_cartographer/analyzers/dag_config_parser.py` | ✓ Yes | `parse_dbt_project_config()`, `extract_model_metadata()`, `extract_source_definitions()` for dbt YAML; Airflow DAG parsing not implemented. |
| `src/agents/surveyor.py` — module graph, PageRank, git velocity, dead code | `src/brownfield_cartographer/agents/surveyor.py` | ✓ Yes | Builds module graph; `_attach_analytics()`: PageRank, `change_velocity_30d`, dead-code candidates, SCC cycles. |
| `src/agents/hydrologist.py` — DataLineageGraph, blast_radius, find_sources/find_sinks | `src/brownfield_cartographer/agents/hydrologist.py` | ✓ Yes | Populates `kg.lineage_graph`; methods `blast_radius()`, `find_sources()`, `find_sinks()`. |
| `src/graph/knowledge_graph.py` — NetworkX wrapper, serialization | `src/brownfield_cartographer/graph/knowledge_graph.py` | ✓ Yes | `KnowledgeGraph` with `module_graph`/`lineage_graph` (NetworkX DiGraph); `save_*`/`load_from_paths()` JSON. |
| `pyproject.toml` with locked deps (uv) | `pyproject.toml` + `uv.lock` | ✓ Yes | Dependencies in pyproject.toml; `uv.lock` generated with `uv lock`. |
| `README.md` — install and run, at least analyze | `README.md` | ✓ Yes | Install via `pip install -e ".[dev]"`; `cartography analyze <repo>` and options documented. |

### 1.2 Cartography artifacts (at least one target codebase) — verified on disk

| Required | Path | In repo? | Notes |
|----------|------|----------|--------|
| Module graph JSON | `.cartography/module_graph.json` | ✓ Yes | Present (e.g. from running analyze on this repo). |
| Lineage graph JSON | `.cartography/lineage_graph.json` | ✓ Yes | Present; partial SQL lineage via sqlglot is acceptable for interim. |

---

## 2. RECONNAISSANCE.md content (manual Day-One analysis)

*Include in the PDF: a short manual Day-One reconnaissance for your chosen target codebase. Below is a template you can fill and paste into the report.*

**Target codebase:** *(e.g. this repo, or dbt-labs/jaffle_shop, or another)*

1. **Primary data ingestion**  
   *(Where does data first enter the system? Which tables/sources?)*

2. **Critical outputs**  
   *(3–5 most important output datasets or endpoints.)*

3. **Blast radius**  
   *(If the most critical module or table failed, what would be affected?)*

4. **Business logic**  
   *(Where is core logic concentrated vs. distributed?)*

5. **Most active files (last 90 days)**  
   *(Which files change most often?)*

*(For interim, you can base this on running the Cartographer and then manually verifying a few answers against the repo.)*

---

## 3. Architecture diagram: four-agent pipeline and data flow

**Data flow (interim scope):**

```
┌─────────────────┐     ┌──────────────────┐     ┌─────────────────────┐
│  CLI (Typer)    │────▶│  Orchestrator    │────▶│  KnowledgeGraph     │
│  analyze /      │     │  run_surveyor()  │     │  (module_graph +     │
│  brief /        │     │  run_hydrologist()│    │   lineage_graph)     │
│  lineage / map  │     │  run_semanticist()│     │  JSON serialize      │
└─────────────────┘     └────────┬─────────┘     └──────────┬──────────┘
                                  │                           │
          ┌───────────────────────┼───────────────────────┐  │
          ▼                       ▼                       ▼  ▼
┌─────────────────┐   ┌─────────────────────┐   ┌─────────────────┐
│  Surveyor       │   │  Hydrologist         │   │  Semanticist     │
│  tree_sitter    │   │  sql_lineage         │   │  summaries       │
│  module graph   │   │  dag_config (dbt)     │   │  Day-One answers  │
│  PageRank,      │   │  blast_radius,       │   │  (Archivist      │
│  git velocity,  │   │  find_sources/sinks   │   │   writes docs)    │
│  dead code      │   │  lineage DAG         │   │                  │
└─────────────────┘   └─────────────────────┘   └─────────────────┘
```

- **Surveyor** → builds `module_graph` (imports, PageRank, change velocity, dead-code candidates, cycles).
- **Hydrologist** → builds `lineage_graph` (datasets, transformations, edges from SQL + dbt metadata).
- **Semanticist** → adds semantic summaries and Day-One answers; **Archivist** writes CODEBASE.md, ONBOARDING_BRIEF.md, RECONNAISSANCE skeleton.
- **Navigator** → used by CLI for `lineage` and `map` queries (upstream/downstream, blast radius style traversal).

---

## 4. Progress summary: what’s working, what’s in progress

**Working:**

- CLI: `analyze` (repo path or GitHub URL), `brief`, `lineage`, `map`, `path`; output dir configurable.
- Orchestrator: Surveyor → Hydrologist → Semanticist in sequence; writes `module_graph.json` and `lineage_graph.json` to `.cartography/`.
- Models: four node types, five edge types, analytical fields (e.g. change_velocity_30d, is_dead_code_candidate); Pydantic + NetworkX serialization/deserialization.
- Tree-sitter: Python AST parsing (imports, functions, classes); `analyze_module()` router by extension.
- SQL lineage: sqlglot multi-dialect; FROM/JOIN/CTE; dbt `ref()` extraction; read vs write metadata; unparseable SQL logged and skipped.
- Surveyor: module graph, PageRank, git velocity (configurable window), dead-code candidates, circular dependency detection (SCC); per-file errors logged and skipped.
- Hydrologist: lineage DAG; blast_radius, find_sources, find_sinks; per-file errors logged and skipped.
- Archivist: CODEBASE.md, ONBOARDING_BRIEF.md, RECONNAISSANCE skeleton; Day-One answers inferred from graphs.

**In progress / partial:**

- Semanticist: deterministic summaries only; no LLM purpose statements or doc-drift detection yet.
- Navigator: structured queries (lineage, map, path); no LangGraph agent or four-tool interface yet.
- DAG config: dbt YAML (sources, model metadata); Airflow DAG parsing not implemented.
- Incremental update (re-analyze only changed files) not implemented.
- `cartography_trace.jsonl` not implemented.

---

## 5. Early accuracy observations

- **Module graph:** For Python repos, import edges and node set match expectations; PageRank and dead-code flags are plausible. High-velocity files align with git history where available.
- **Lineage graph:** For dbt-style SQL (e.g. jaffle_shop), table→model edges from sqlglot and ref() match the expected DAG; dbt schema/metadata enrich nodes. Partial lineage is acceptable for interim.
- **Day-One answers:** Inferred from graph structure (sources, out-degree, descendants, business-logic scoring, commit counts). Correct for small examples; should be validated on a second codebase for the final report.

---

## 6. Known gaps and plan for final submission

**Gaps:**

- No LLM-powered purpose statements or docstring drift detection.
- No LangGraph Navigator agent with four tools (find_implementation, trace_lineage, blast_radius, explain_module).
- No cartography_trace.jsonl or incremental update mode.
- Limited DAG parsing (dbt only; no Airflow operator extraction).
- No notebook (.ipynb) or Python dataframe read/write lineage.

**Plan for final (Sunday March 15):**

1. Add Semanticist LLM integration (purpose statements, domain clustering, Day-One synthesis).
2. Implement Navigator as LangGraph agent with the four tools and evidence citation.
3. Add cartography_trace.jsonl and incremental update (git diff).
4. Extend DAG/config parsing (Airflow if time permits).
5. Run on 2+ target codebases; produce CODEBASE.md, onboarding_brief.md, trace; complete PDF and video demo per challenge.

---

## 7. How to generate this report as PDF

1. Fill Section 2 (RECONNAISSANCE) for your chosen target.
2. Export this markdown to PDF (e.g. VS Code “Markdown PDF”, Pandoc, or print to PDF from a viewer).
3. Submit the PDF together with the GitHub repo and (if applicable) a zip of `.cartography/` for at least one target codebase.

---

*Document derived from: `ref/TRP 1 Challenge Week 4_ The Brownfield Cartographer.docx`.*
