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

## Interim delivery (Week 4)

For the **interim delivery (Thursday March 12)**, see **[docs/INTERIM_DELIVERY.md](docs/INTERIM_DELIVERY.md)** for the required Single PDF Report content (checklist, RECONNAISSANCE, architecture, progress, accuracy, gaps, plan). Use [docs/RECONNAISSANCE_TEMPLATE.md](docs/RECONNAISSANCE_TEMPLATE.md) to draft manual Day-One analysis for your chosen target codebase.

