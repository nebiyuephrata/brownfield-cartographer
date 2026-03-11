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
cartography analyze /path/to/target/repo --output-dir .cartography --format json
```

The CLI is backed by Typer and delegates to the `Orchestrator` to run the Surveyor and Hydrologist agents.

