import { memo } from "react";
import type { RunResponse } from "../api/cartography";

interface RunDetailProps {
  run?: RunResponse | null;
  moduleCount: number;
  lineageCount: number;
  onLoadGraphs?: () => void;
}

const RunDetail = memo(({ run, moduleCount, lineageCount, onLoadGraphs }: RunDetailProps) => {
  if (!run) {
    return (
      <section className="glass rounded-2xl p-5">
        <h2 className="text-sm font-semibold text-graphite-700 dark:text-graphite-100">Run detail</h2>
        <p className="mt-2 text-xs text-graphite-500 dark:text-graphite-300">
          Select a run to view details and load its graphs.
        </p>
      </section>
    );
  }

  return (
    <section className="glass rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-graphite-700 dark:text-graphite-100">Run detail</h2>
          <p className="text-xs text-graphite-500 dark:text-graphite-300">Run id: {run.run_id}</p>
        </div>
        <button
          onClick={onLoadGraphs}
          className="rounded-full border border-graphite-200 px-3 py-1 text-xs font-semibold text-graphite-600 hover:border-signal-500 dark:border-graphite-700 dark:text-graphite-200"
        >
          Load graphs
        </button>
      </div>
      <div className="mt-4 grid gap-3 text-xs text-graphite-600 dark:text-graphite-200">
        <div>
          <span className="font-semibold text-graphite-800 dark:text-graphite-100">Repo:</span> {run.repo_path}
        </div>
        <div>
          <span className="font-semibold text-graphite-800 dark:text-graphite-100">Output:</span> {run.output_dir}
        </div>
        <div>
          <span className="font-semibold text-graphite-800 dark:text-graphite-100">Status:</span> {run.status}
        </div>
        <div>
          <span className="font-semibold text-graphite-800 dark:text-graphite-100">Started:</span>{" "}
          {new Date(run.started_at).toLocaleString()}
        </div>
        {run.completed_at ? (
          <div>
            <span className="font-semibold text-graphite-800 dark:text-graphite-100">Completed:</span>{" "}
            {new Date(run.completed_at).toLocaleString()}
          </div>
        ) : null}
        {run.error ? (
          <div className="rounded-xl border border-rose-500/40 bg-rose-500/10 px-3 py-2 text-[11px] text-rose-200">
            {run.error}
          </div>
        ) : null}
        <div className="flex flex-wrap gap-3">
          <span className="rounded-full border border-graphite-200 px-3 py-1 text-[11px] text-graphite-500 dark:border-graphite-700 dark:text-graphite-300">
            Module nodes: {moduleCount}
          </span>
          <span className="rounded-full border border-graphite-200 px-3 py-1 text-[11px] text-graphite-500 dark:border-graphite-700 dark:text-graphite-300">
            Lineage nodes: {lineageCount}
          </span>
        </div>
      </div>
    </section>
  );
});

RunDetail.displayName = "RunDetail";

export default RunDetail;
