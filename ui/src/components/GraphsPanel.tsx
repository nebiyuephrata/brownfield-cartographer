import { memo, useMemo, useState } from "react";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import ReactFlow, { Background, Controls, MiniMap } from "reactflow";
import type { GraphPayload } from "../api/cartography";
import { activitySeries } from "../data/mock";
import { selectGraphFocus } from "../api/helpers";

interface GraphsPanelProps {
  moduleGraph?: GraphPayload | null;
  lineageGraph?: GraphPayload | null;
}

type FlowGraph = "module" | "lineage" | null;

const GraphsPanel = memo(({ moduleGraph, lineageGraph }: GraphsPanelProps) => {
  const [fullscreen, setFullscreen] = useState<FlowGraph>(null);
  const focusModule = useMemo(() => selectGraphFocus(moduleGraph, 14), [moduleGraph]);
  const focusLineage = useMemo(() => selectGraphFocus(lineageGraph, 14), [lineageGraph]);

  const flowNodes = useMemo(
    () =>
      (focusModule?.nodes ?? []).map((node, index) => ({
        id: node.id,
        data: { label: String(node.id) },
        position: { x: 50 + index * 120, y: 50 + (index % 2) * 120 },
        style: {
          background: "#0f172a",
          color: "#e2e8f0",
          borderRadius: 12,
          padding: 12,
          border: "1px solid rgba(148,163,184,0.35)"
        }
      })),
    [focusModule]
  );

  const flowEdges = useMemo(
    () =>
      (focusModule?.edges ?? []).map((edge, index) => ({
        id: `edge-${index}`,
        source: edge.source,
        target: edge.target,
        animated: true,
        style: { stroke: "#52e1b2" }
      })),
    [focusModule]
  );

  const lineageNodes = useMemo(
    () =>
      (focusLineage?.nodes ?? []).map((node, index) => ({
        id: node.id,
        data: { label: String(node.id) },
        position: { x: 50 + index * 120, y: 50 + (index % 2) * 120 },
        style: {
          background: "#111827",
          color: "#e2e8f0",
          borderRadius: 12,
          padding: 12,
          border: "1px solid rgba(148,163,184,0.35)"
        }
      })),
    [focusLineage]
  );

  const lineageEdges = useMemo(
    () =>
      (focusLineage?.edges ?? []).map((edge, index) => ({
        id: `lineage-edge-${index}`,
        source: edge.source,
        target: edge.target,
        animated: true,
        style: { stroke: "#7aa5ff" }
      })),
    [focusLineage]
  );

  return (
    <section className="glass rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-graphite-700 dark:text-graphite-100">Graph signals</h2>
          <p className="text-xs text-graphite-500 dark:text-graphite-300">Module growth and dependency health.</p>
        </div>
        <div className="flex items-center gap-2 text-xs">
          <span className="rounded-full border border-graphite-200 px-3 py-1 text-graphite-600 dark:border-graphite-700 dark:text-graphite-200">
            {moduleGraph?.edges?.length ?? 0} module edges
          </span>
          <span className="rounded-full border border-graphite-200 px-3 py-1 text-graphite-600 dark:border-graphite-700 dark:text-graphite-200">
            {lineageGraph?.edges?.length ?? 0} lineage edges
          </span>
        </div>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-[1.2fr_1fr]">
        <div className="h-72 rounded-2xl bg-white/80 p-3 dark:bg-graphite-900/70">
          <p className="mb-2 text-xs font-semibold text-graphite-600 dark:text-graphite-300">Modules analyzed</p>
          <ResponsiveContainer width="100%" height="100%">
            <AreaChart data={activitySeries} margin={{ left: -16, right: 12 }}>
              <XAxis dataKey="name" tick={{ fill: "#94a3b8", fontSize: 10 }} axisLine={false} tickLine={false} />
              <YAxis tick={{ fill: "#94a3b8", fontSize: 10 }} axisLine={false} tickLine={false} />
              <Tooltip
                contentStyle={{
                  borderRadius: 12,
                  border: "none",
                  background: "#0f172a",
                  color: "#e2e8f0",
                  fontSize: 12
                }}
              />
              <Area type="monotone" dataKey="modules" stroke="#52e1b2" fill="rgba(82,225,178,0.25)" />
            </AreaChart>
          </ResponsiveContainer>
        </div>
        <div className="h-72 rounded-2xl bg-white/80 p-3 dark:bg-graphite-900/70">
          <div className="mb-2 flex items-center justify-between text-xs font-semibold text-graphite-600 dark:text-graphite-300">
            <span>Dependency flow</span>
            <button
              onClick={() => setFullscreen("module")}
              className="rounded-full border border-graphite-200 px-2 py-1 text-[10px] text-graphite-500 hover:border-signal-500 dark:border-graphite-700 dark:text-graphite-300"
            >
              Full screen
            </button>
          </div>
          <div className="h-[calc(100%-28px)] rounded-xl border border-graphite-200/60 dark:border-graphite-700">
            <ReactFlow nodes={flowNodes} edges={flowEdges} fitView>
              <MiniMap />
              <Controls />
              <Background />
            </ReactFlow>
          </div>
        </div>
      </div>
      <div className="mt-4 h-72 rounded-2xl bg-white/80 p-3 dark:bg-graphite-900/70">
        <div className="mb-2 flex items-center justify-between text-xs font-semibold text-graphite-600 dark:text-graphite-300">
          <span>Lineage flow</span>
          <button
            onClick={() => setFullscreen("lineage")}
            className="rounded-full border border-graphite-200 px-2 py-1 text-[10px] text-graphite-500 hover:border-signal-500 dark:border-graphite-700 dark:text-graphite-300"
          >
            Full screen
          </button>
        </div>
        <div className="h-[calc(100%-28px)] rounded-xl border border-graphite-200/60 dark:border-graphite-700">
          <ReactFlow nodes={lineageNodes} edges={lineageEdges} fitView>
            <MiniMap />
            <Controls />
            <Background />
          </ReactFlow>
        </div>
      </div>
      {fullscreen ? (
        <div className="fixed inset-0 z-50 flex items-center justify-center bg-graphite-900/90 p-6">
          <div className="flex h-full w-full flex-col rounded-3xl bg-graphite-950 p-4">
            <div className="mb-3 flex items-center justify-between text-xs text-graphite-200">
              <span>{fullscreen === "module" ? "Module dependency flow" : "Lineage flow"}</span>
              <button
                onClick={() => setFullscreen(null)}
                className="rounded-full border border-graphite-700 px-3 py-1 text-[11px] text-graphite-200"
              >
                Exit full screen
              </button>
            </div>
            <div className="flex-1 rounded-2xl border border-graphite-800 bg-graphite-900">
              <ReactFlow
                nodes={fullscreen === "module" ? flowNodes : lineageNodes}
                edges={fullscreen === "module" ? flowEdges : lineageEdges}
                fitView
              >
                <MiniMap />
                <Controls />
                <Background />
              </ReactFlow>
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
});

GraphsPanel.displayName = "GraphsPanel";

export default GraphsPanel;
