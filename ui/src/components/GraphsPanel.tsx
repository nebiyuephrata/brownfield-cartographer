import { memo, useMemo } from "react";
import { Area, AreaChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import ReactFlow, { Background, Controls, MiniMap } from "reactflow";
import { activitySeries, moduleEdges, moduleNodes } from "../data/mock";

const GraphsPanel = memo(() => {
  const flowNodes = useMemo(
    () =>
      moduleNodes.map((node, index) => ({
        id: node.id,
        data: { label: node.label },
        position: { x: 50 + index * 120, y: 50 + (index % 2) * 120 },
        style: {
          background: "#0f172a",
          color: "#e2e8f0",
          borderRadius: 12,
          padding: 12,
          border: "1px solid rgba(148,163,184,0.35)"
        }
      })),
    []
  );

  const flowEdges = useMemo(
    () =>
      moduleEdges.map((edge) => ({
        ...edge,
        animated: true,
        style: { stroke: "#52e1b2" }
      })),
    []
  );

  return (
    <section className="glass rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-graphite-700 dark:text-graphite-100">Graph signals</h2>
          <p className="text-xs text-graphite-500 dark:text-graphite-300">Module growth and dependency health.</p>
        </div>
        <span className="rounded-full border border-graphite-200 px-3 py-1 text-xs text-graphite-600 dark:border-graphite-700 dark:text-graphite-200">
          82 edges mapped
        </span>
      </div>
      <div className="mt-4 grid gap-4 lg:grid-cols-[1.2fr_1fr]">
        <div className="h-56 rounded-2xl bg-white/80 p-3 dark:bg-graphite-900/70">
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
        <div className="h-56 rounded-2xl bg-white/80 p-3 dark:bg-graphite-900/70">
          <p className="mb-2 text-xs font-semibold text-graphite-600 dark:text-graphite-300">
            Dependency flow
          </p>
          <div className="h-[calc(100%-28px)] rounded-xl border border-graphite-200/60 dark:border-graphite-700">
            <ReactFlow nodes={flowNodes} edges={flowEdges} fitView>
              <MiniMap />
              <Controls />
              <Background />
            </ReactFlow>
          </div>
        </div>
      </div>
    </section>
  );
});

GraphsPanel.displayName = "GraphsPanel";

export default GraphsPanel;
