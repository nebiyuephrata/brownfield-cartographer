import { memo } from "react";
import type { RunResponse } from "../api/cartography";

interface RunHistoryProps {
  runs: RunResponse[];
  activeRunId?: string | null;
  onSelect?: (run: RunResponse) => void;
}

const RunHistory = memo(({ runs, activeRunId, onSelect }: RunHistoryProps) => {
  return (
    <section className="glass rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-graphite-700 dark:text-graphite-100">Run history</h2>
          <p className="text-xs text-graphite-500 dark:text-graphite-300">Recent analysis sessions.</p>
        </div>
        <span className="rounded-full border border-graphite-200 px-3 py-1 text-xs text-graphite-600 dark:border-graphite-700 dark:text-graphite-200">
          {runs.length} runs
        </span>
      </div>
      <div className="mt-4 space-y-3">
        {runs.length === 0 ? (
          <div className="rounded-xl border border-dashed border-graphite-200 px-4 py-6 text-center text-xs text-graphite-500 dark:border-graphite-700 dark:text-graphite-300">
            No runs yet. Start an analysis to populate history.
          </div>
        ) : (
          runs
            .slice()
            .reverse()
            .slice(0, 6)
            .map((run) => (
              <button
                key={run.run_id}
                onClick={() => onSelect?.(run)}
                className={`w-full rounded-xl border px-4 py-3 text-left text-xs transition hover:border-signal-500 ${
                  run.run_id === activeRunId
                    ? "border-signal-500 bg-signal-500/10"
                    : "border-graphite-200 bg-white/70 dark:border-graphite-700 dark:bg-graphite-900/60"
                }`}
              >
                <div className="flex items-center justify-between">
                  <span className="font-semibold text-graphite-700 dark:text-graphite-100">
                    {run.repo_path}
                  </span>
                  <span className="rounded-full border border-graphite-200 px-2 py-1 text-[10px] text-graphite-500 dark:border-graphite-700 dark:text-graphite-300">
                    {run.status}
                  </span>
                </div>
                <div className="mt-2 text-[11px] text-graphite-500 dark:text-graphite-300">
                  Started: {new Date(run.started_at).toLocaleString()}
                </div>
              </button>
            ))
        )}
      </div>
    </section>
  );
});

RunHistory.displayName = "RunHistory";

export default RunHistory;
