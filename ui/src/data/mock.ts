export const progressSteps = [
  { id: "scan", label: "Repository scan", progress: 86 },
  { id: "deps", label: "Module dependency graph", progress: 72 },
  { id: "lineage", label: "Lineage extraction", progress: 64 },
  { id: "summaries", label: "Semantic summaries", progress: 42 }
];

export const activitySeries = [
  { name: "Day 1", modules: 14, edges: 46 },
  { name: "Day 2", modules: 19, edges: 55 },
  { name: "Day 3", modules: 24, edges: 62 },
  { name: "Day 4", modules: 31, edges: 70 },
  { name: "Day 5", modules: 36, edges: 82 }
];

export const moduleNodes = [
  { id: "ingest", label: "ingest" },
  { id: "staging", label: "staging" },
  { id: "mart", label: "marts" },
  { id: "orchestrator", label: "orchestrator" },
  { id: "alerts", label: "alerts" }
];

export const moduleEdges = [
  { id: "e1", source: "ingest", target: "staging" },
  { id: "e2", source: "staging", target: "mart" },
  { id: "e3", source: "orchestrator", target: "ingest" },
  { id: "e4", source: "orchestrator", target: "alerts" },
  { id: "e5", source: "mart", target: "alerts" }
];

export const sampleReadme = `# Target Repo README\n\nThis panel renders README content from the selected repository.\n\n- Click *Load Markdown* to preview local files.\n- When the backend is wired, this will stream markdown from analysis output.\n\n## Quick Start\n\n1. Connect a repo\n2. Run analysis\n3. Explore graphs and onboarding briefs\n`;

export const sampleOnboarding = `# Onboarding Brief\n\n## What does this system do?\n\nIt consolidates ingestion, transformation, and activation data flows.\n\n## Blast radius\n\n- Changes in *staging* affect marts and alerting.\n- Changes in *orchestrator* impact ingestion scheduling.\n\n## Gaps\n\n- No ownership metadata for some datasets.\n- Missing tests for alerting rules.\n`;
