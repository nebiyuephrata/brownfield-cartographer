import { memo, useEffect, useMemo, useState } from "react";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import ReactFlow, { Background, Controls, MiniMap } from "reactflow";
import type { GraphPayload } from "../api/cartography";
import { activitySeries } from "../data/mock";

interface GraphsPanelProps {
  moduleGraph?: GraphPayload | null;
  lineageGraph?: GraphPayload | null;
  focusLineageNodeId?: string | null;
}

type FlowGraph = "module" | "lineage" | null;

const GraphsPanel = memo(({ moduleGraph, lineageGraph, focusLineageNodeId }: GraphsPanelProps) => {
  const [fullscreen, setFullscreen] = useState<FlowGraph>(null);
  const [moduleSearch, setModuleSearch] = useState("");
  const [lineageSearch, setLineageSearch] = useState("");
  const [moduleLimit, setModuleLimit] = useState(24);
  const [lineageLimit, setLineageLimit] = useState(24);
  const [selectedModule, setSelectedModule] = useState<string | null>(null);
  const [selectedLineage, setSelectedLineage] = useState<string | null>(null);
  const [animateEdges, setAnimateEdges] = useState(true);

  const sliceGraph = (graph: GraphPayload | null | undefined, limit: number, query: string) => {
    if (!graph || !graph.nodes || !graph.edges) {
      return { nodes: [], edges: [] as GraphPayload["edges"] };
    }
    const lowered = query.trim().toLowerCase();
    const nodes = graph.nodes.filter((node) => (lowered ? String(node.id).toLowerCase().includes(lowered) : true));
    const limited = nodes.slice(0, Math.max(6, limit));
    const nodeSet = new Set(limited.map((node) => node.id));
    const edges = graph.edges.filter((edge) => nodeSet.has(edge.source) && nodeSet.has(edge.target));
    return { nodes: limited, edges };
  };

  const focusModule = useMemo(
    () => sliceGraph(moduleGraph, moduleLimit, moduleSearch),
    [moduleGraph, moduleLimit, moduleSearch]
  );
  const focusLineage = useMemo(
    () => sliceGraph(lineageGraph, lineageLimit, lineageSearch),
    [lineageGraph, lineageLimit, lineageSearch]
  );

  useEffect(() => {
    if (focusLineageNodeId) {
      setFullscreen("lineage");
      setSelectedLineage(focusLineageNodeId);
    }
  }, [focusLineageNodeId]);

  const moduleDegrees = useMemo(() => {
    const degrees = new Map<string, { in: number; out: number }>();
    for (const edge of focusModule.edges) {
      degrees.set(edge.source, { in: degrees.get(edge.source)?.in ?? 0, out: (degrees.get(edge.source)?.out ?? 0) + 1 });
      degrees.set(edge.target, { in: (degrees.get(edge.target)?.in ?? 0) + 1, out: degrees.get(edge.target)?.out ?? 0 });
    }
    return degrees;
  }, [focusModule.edges]);

  const lineageDegrees = useMemo(() => {
    const degrees = new Map<string, { in: number; out: number }>();
    for (const edge of focusLineage.edges) {
      degrees.set(edge.source, {
        in: degrees.get(edge.source)?.in ?? 0,
        out: (degrees.get(edge.source)?.out ?? 0) + 1
      });
      degrees.set(edge.target, {
        in: (degrees.get(edge.target)?.in ?? 0) + 1,
        out: degrees.get(edge.target)?.out ?? 0
      });
    }
    return degrees;
  }, [focusLineage.edges]);

  const flowNodes = useMemo(
    () =>
      (focusModule?.nodes ?? []).map((node, index) => ({
        id: node.id,
        data: { label: String(node.id) },
        position: {
          x: 200 + Math.cos(index / 2.5) * 220 + (index % 3) * 30,
          y: 140 + Math.sin(index / 2.5) * 160
        },
        style: {
          background: "#0f172a",
          color: "#e2e8f0",
          borderRadius: 12,
          padding: 12,
          border: node.id === selectedModule ? "2px solid #52e1b2" : "1px solid rgba(148,163,184,0.35)",
          boxShadow: node.id === selectedModule ? "0 0 0 2px rgba(82,225,178,0.35)" : undefined
        }
      })),
    [focusModule, selectedModule]
  );

  const flowEdges = useMemo(
    () =>
      (focusModule?.edges ?? []).map((edge, index) => ({
        id: `edge-${index}`,
        source: edge.source,
        target: edge.target,
        animated: animateEdges,
        style: { stroke: "#52e1b2" }
      })),
    [focusModule, animateEdges]
  );

  const lineageNodes = useMemo(
    () =>
      (focusLineage?.nodes ?? []).map((node, index) => ({
        id: node.id,
        data: { label: String(node.id) },
        position: {
          x: 220 + Math.cos(index / 2.7) * 230 + (index % 4) * 20,
          y: 150 + Math.sin(index / 2.7) * 170
        },
        style: {
          background: "#111827",
          color: "#e2e8f0",
          borderRadius: 12,
          padding: 12,
          border:
            node.id === focusLineageNodeId || node.id === selectedLineage
              ? "2px solid #f59e0b"
              : "1px solid rgba(148,163,184,0.35)",
          boxShadow: node.id === selectedLineage ? "0 0 0 2px rgba(245,158,11,0.4)" : undefined
        }
      })),
    [focusLineage, focusLineageNodeId, selectedLineage]
  );

  const lineageEdges = useMemo(
    () =>
      (focusLineage?.edges ?? []).map((edge, index) => ({
        id: `lineage-edge-${index}`,
        source: edge.source,
        target: edge.target,
        animated: animateEdges,
        style: { stroke: "#7aa5ff" }
      })),
    [focusLineage, animateEdges]
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
          <div className="mb-3 flex flex-wrap items-center gap-2 text-[10px] text-graphite-500 dark:text-graphite-300">
            <input
              value={moduleSearch}
              onChange={(event) => setModuleSearch(event.target.value)}
              placeholder="Search module..."
              className="rounded-full border border-graphite-200 bg-white/70 px-3 py-1 text-[10px] text-graphite-600 dark:border-graphite-700 dark:bg-graphite-900/70 dark:text-graphite-200"
            />
            <label className="flex items-center gap-2">
              Nodes
              <input
                type="range"
                min={8}
                max={60}
                value={moduleLimit}
                onChange={(event) => setModuleLimit(Number(event.target.value))}
                className="accent-signal-500"
              />
            </label>
            <label className="flex items-center gap-2">
              Animate
              <input type="checkbox" checked={animateEdges} onChange={() => setAnimateEdges((prev) => !prev)} />
            </label>
          </div>
          <div className="h-[calc(100%-28px)] rounded-xl border border-graphite-200/60 dark:border-graphite-700">
            <ReactFlow
              nodes={flowNodes}
              edges={flowEdges}
              fitView
              className="h-full w-full"
              onNodeClick={(_, node) => setSelectedModule(node.id)}
            >
              <MiniMap />
              <Controls />
              <Background />
            </ReactFlow>
          </div>
          {selectedModule ? (
            <div className="mt-3 rounded-xl border border-graphite-200 bg-white/70 p-3 text-[10px] text-graphite-600 dark:border-graphite-700 dark:bg-graphite-900/70 dark:text-graphite-200">
              <div className="font-semibold text-graphite-800 dark:text-graphite-100">Selected: {selectedModule}</div>
              <div>In: {moduleDegrees.get(selectedModule)?.in ?? 0} · Out: {moduleDegrees.get(selectedModule)?.out ?? 0}</div>
            </div>
          ) : null}
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
        <div className="mb-3 flex flex-wrap items-center gap-2 text-[10px] text-graphite-500 dark:text-graphite-300">
          <input
            value={lineageSearch}
            onChange={(event) => setLineageSearch(event.target.value)}
            placeholder="Search dataset..."
            className="rounded-full border border-graphite-200 bg-white/70 px-3 py-1 text-[10px] text-graphite-600 dark:border-graphite-700 dark:bg-graphite-900/70 dark:text-graphite-200"
          />
          <label className="flex items-center gap-2">
            Nodes
            <input
              type="range"
              min={8}
              max={60}
              value={lineageLimit}
              onChange={(event) => setLineageLimit(Number(event.target.value))}
              className="accent-signal-500"
            />
          </label>
        </div>
        <div className="h-[calc(100%-28px)] rounded-xl border border-graphite-200/60 dark:border-graphite-700">
          <ReactFlow
            nodes={lineageNodes}
            edges={lineageEdges}
            fitView
            className="h-full w-full"
            onNodeClick={(_, node) => setSelectedLineage(node.id)}
          >
            <MiniMap />
            <Controls />
            <Background />
          </ReactFlow>
        </div>
        {selectedLineage ? (
          <div className="mt-3 rounded-xl border border-graphite-200 bg-white/70 p-3 text-[10px] text-graphite-600 dark:border-graphite-700 dark:bg-graphite-900/70 dark:text-graphite-200">
            <div className="font-semibold text-graphite-800 dark:text-graphite-100">Selected: {selectedLineage}</div>
            <div>In: {lineageDegrees.get(selectedLineage)?.in ?? 0} · Out: {lineageDegrees.get(selectedLineage)?.out ?? 0}</div>
          </div>
        ) : null}
      </div>
      {fullscreen ? (
        <div className="fixed inset-0 z-[80] flex items-center justify-center bg-graphite-900/90 p-6">
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
            <div className="mb-3 flex items-center gap-3 text-[11px] text-graphite-300">
              <span className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-signal-500" />
                Module edge
              </span>
              <span className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full bg-[#7aa5ff]" />
                Lineage edge
              </span>
              <span className="flex items-center gap-2">
                <span className="h-2 w-2 rounded-full border border-graphite-500" />
                Node
              </span>
            </div>
            <div className="flex-1 rounded-2xl border border-graphite-800 bg-graphite-900">
              {(fullscreen === "module" ? flowNodes : lineageNodes).length === 0 ? (
                <div className="flex h-full items-center justify-center text-xs text-graphite-400">
                  No nodes available yet. Run analysis to populate the graph.
                </div>
              ) : (
                <ReactFlow
                  nodes={fullscreen === "module" ? flowNodes : lineageNodes}
                  edges={fullscreen === "module" ? flowEdges : lineageEdges}
                  fitView
                  className="h-full w-full"
                >
                  <MiniMap />
                  <Controls />
                  <Background />
                </ReactFlow>
              )}
            </div>
          </div>
        </div>
      ) : null}
    </section>
  );
});

GraphsPanel.displayName = "GraphsPanel";

export default GraphsPanel;
