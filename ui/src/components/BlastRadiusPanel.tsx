import { memo, useMemo } from "react";
import type { GraphPayload } from "../api/cartography";

interface BlastRadiusPanelProps {
  lineageGraph?: GraphPayload | null;
  onSelectNode?: (nodeId: string) => void;
}

function computeBlastRadius(graph?: GraphPayload | null, limit = 200) {
  if (!graph || !graph.nodes || !graph.edges) {
    return [] as Array<{ id: string; reach: number }>;
  }
  const nodes = graph.nodes.slice(0, limit).map((node) => node.id);
  const adjacency = new Map<string, string[]>();
  for (const node of nodes) {
    adjacency.set(node, []);
  }
  for (const edge of graph.edges) {
    if (adjacency.has(edge.source) && adjacency.has(edge.target)) {
      adjacency.get(edge.source)!.push(edge.target);
    }
  }

  const scores: Array<{ id: string; reach: number }> = [];
  for (const node of nodes) {
    const visited = new Set<string>();
    const stack = [...(adjacency.get(node) ?? [])];
    while (stack.length > 0) {
      const current = stack.pop() as string;
      if (visited.has(current)) continue;
      visited.add(current);
      const neighbors = adjacency.get(current) ?? [];
      for (const neighbor of neighbors) {
        if (!visited.has(neighbor)) {
          stack.push(neighbor);
        }
      }
    }
    scores.push({ id: node, reach: visited.size });
  }

  scores.sort((a, b) => b.reach - a.reach);
  return scores.slice(0, 6);
}

const BlastRadiusPanel = memo(({ lineageGraph, onSelectNode }: BlastRadiusPanelProps) => {
  const top = useMemo(() => computeBlastRadius(lineageGraph), [lineageGraph]);
  const maxReach = top[0]?.reach ?? 1;

  return (
    <section className="glass rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-graphite-700 dark:text-graphite-100">Blast radius</h2>
          <p className="text-xs text-graphite-500 dark:text-graphite-300">
            Highest downstream impact in the lineage graph.
          </p>
        </div>
        <span className="rounded-full border border-graphite-200 px-3 py-1 text-xs text-graphite-600 dark:border-graphite-700 dark:text-graphite-200">
          Top {top.length}
        </span>
      </div>
      <div className="mt-4 space-y-3">
        {top.length === 0 ? (
          <div className="rounded-xl border border-dashed border-graphite-200 px-4 py-6 text-center text-xs text-graphite-500 dark:border-graphite-700 dark:text-graphite-300">
            Run lineage analysis to compute blast radius.
          </div>
        ) : (
          top.map((item) => (
            <button
              key={item.id}
              onClick={() => onSelectNode?.(item.id)}
              className="w-full space-y-2 rounded-xl border border-transparent p-2 text-left transition hover:border-signal-500"
            >
              <div className="flex items-center justify-between text-xs text-graphite-600 dark:text-graphite-200">
                <span className="truncate">{item.id}</span>
                <span>{item.reach} downstream</span>
              </div>
              <div className="h-2 rounded-full bg-graphite-200/70 dark:bg-graphite-800">
                <div
                  className="h-2 rounded-full bg-gradient-to-r from-signal-500 to-signal-400"
                  style={{ width: `${Math.max(6, (item.reach / maxReach) * 100)}%` }}
                />
              </div>
            </button>
          ))
        )}
      </div>
    </section>
  );
});

BlastRadiusPanel.displayName = "BlastRadiusPanel";

export default BlastRadiusPanel;
