import { memo } from "react";
import type { ToastItem } from "./Toast";

interface ErrorLogPanelProps {
  logs: ToastItem[];
}

const ErrorLogPanel = memo(({ logs }: ErrorLogPanelProps) => {
  return (
    <section className="glass rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-graphite-700 dark:text-graphite-100">Error log</h2>
          <p className="text-xs text-graphite-500 dark:text-graphite-300">Latest warnings and failures.</p>
        </div>
        <span className="rounded-full border border-graphite-200 px-3 py-1 text-xs text-graphite-600 dark:border-graphite-700 dark:text-graphite-200">
          {logs.length}
        </span>
      </div>
      <div className="mt-4 space-y-3">
        {logs.length === 0 ? (
          <div className="rounded-xl border border-dashed border-graphite-200 px-4 py-6 text-center text-xs text-graphite-500 dark:border-graphite-700 dark:text-graphite-300">
            No errors logged yet.
          </div>
        ) : (
          logs.slice(-6).map((log) => (
            <div
              key={log.id}
              className="rounded-xl border border-rose-500/30 bg-rose-500/10 px-4 py-3 text-xs text-rose-100"
            >
              {log.message}
            </div>
          ))
        )}
      </div>
    </section>
  );
});

ErrorLogPanel.displayName = "ErrorLogPanel";

export default ErrorLogPanel;
