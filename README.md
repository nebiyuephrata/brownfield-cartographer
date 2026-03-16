# Brownfield Cartographer

Brownfield Cartographer is a codebase intelligence tool for data engineering repositories. It statically analyzes code and configuration to build:

- Module dependency graphs
- SQL/data lineage graphs
- Evidence-backed onboarding and architecture artifacts

This repository currently contains the core skeleton and agents for early experiments.

## Installation (editable)

From the project root:

```bash
pip install -e ".[dev]"
```

## CLI Usage

Once installed, a `cartography` CLI is available:

```bash
# Run full analysis and write graphs into .cartography/
cartography analyze /path/to/target/repo --output-dir .cartography --format json

# Run analysis but skip SQL/data lineage for faster iteration
cartography analyze /path/to/target/repo --output-dir .cartography --skip-lineage

# Run analysis without computing semantic summaries
cartography analyze /path/to/target/repo --output-dir .cartography --no-semantic

# Generate onboarding docs (markdown files) using existing or freshly computed graphs
cartography brief /path/to/target/repo --output-dir .cartography --format markdown

# Emit a compact JSON summary of Day-One onboarding answers (useful in CI)
cartography brief /path/to/target/repo --output-dir .cartography --format json-summary

# Inspect dataset lineage (human-readable)
cartography lineage /path/to/target/repo fct_orders --output-dir .cartography

# Inspect dataset lineage as JSON (machine-readable)
cartography lineage /path/to/target/repo fct_orders --output-dir .cartography --json

# Inspect module dependencies (human-readable)
cartography map /path/to/target/repo some.package.module --output-dir .cartography

# Inspect module dependencies as JSON (machine-readable)
cartography map /path/to/target/repo some.package.module --output-dir .cartography --json
```

The CLI is backed by Typer and delegates to the `Orchestrator` to run the Surveyor and Hydrologist agents, while the Archivist and Navigator agents power onboarding briefs and navigation commands.

## UI (React + Vite)

A modern, responsive UI lives in `ui/` and provides:

- Live progress and module scope controls
- Graph visualizations (module growth + dependency flow)
- Chat bar for codebase questions (blast radius, ownership, gaps)
- Markdown viewer for README + onboarding briefs
- LLM provider routing with fallback models + quota switch

### Local dev

```bash
cd ui
npm install
npm run dev
```

Create a local env file from the provided template:

```bash
cp .env.example .env
```

> Note: the frontend only reads `VITE_*` variables at build time. For production, store secrets on a backend and proxy requests.

### API service (optional but recommended)

The UI expects a small API to run analysis and serve graph/markdown outputs:

```bash
pip install -e ".[api]"
cartography-api
```

Environment:

- `CARTOGRAPHY_API_PORT` (default `8000`)
- `CARTOGRAPHY_UI_ORIGINS` (comma-separated, default `*`)
- `OPENROUTER_API_KEY`, `OPENROUTER_MODEL`, `OLLAMA_MODEL`, `OLLAMA_HOST` (if you want semantic summaries)

Then set `VITE_API_BASE_URL` in `ui/.env` to match the API host.

## Architecture (High level)

**CLI pipeline**

- `cartography analyze` generates module + lineage graphs in `.cartography/`.
- `cartography brief` uses the graphs to generate onboarding markdown and summaries.

**UI pipeline**

- Vite + React + TypeScript + Tailwind.
- Graphs rendered with `recharts` and `reactflow`.
- Markdown rendered with `react-markdown` + `remark-gfm`.
- LLM routing settings are local state today; hook to a backend service to persist settings and call providers.

**Suggested integration**

Expose the CLI outputs via a small API layer (e.g., FastAPI) so the UI can stream:

- Progress events from analysis runs
- Graph JSON from `.cartography/`
- Generated markdown for README + onboarding briefs

## Interim delivery (Week 4)

For the **interim delivery (Thursday March 12)**, see **[docs/INTERIM_DELIVERY.md](docs/INTERIM_DELIVERY.md)** for the required Single PDF Report content (checklist, RECONNAISSANCE, architecture, progress, accuracy, gaps, plan). Use [docs/RECONNAISSANCE_TEMPLATE.md](docs/RECONNAISSANCE_TEMPLATE.md) to draft manual Day-One analysis for your chosen target codebase.
