import { memo } from "react";

interface Step {
  id: string;
  label: string;
  progress: number;
}

interface ProgressPanelProps {
  steps: Step[];
  overall: number;
}

const ProgressPanel = memo(({ steps, overall }: ProgressPanelProps) => {
  return (
    <section className="glass rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-graphite-700 dark:text-graphite-100">Live progress</h2>
          <p className="text-xs text-graphite-500 dark:text-graphite-300">Streaming from cartography agents.</p>
        </div>
        <div className="rounded-full bg-signal-500/20 px-3 py-1 text-xs font-semibold text-signal-600">
          {overall}%
        </div>
      </div>
      <div className="mt-4 space-y-3">
        {steps.map((step) => (
          <div key={step.id} className="space-y-2">
            <div className="flex items-center justify-between text-xs text-graphite-600 dark:text-graphite-200">
              <span>{step.label}</span>
              <span>{step.progress}%</span>
            </div>
            <div className="h-2 rounded-full bg-graphite-200/70 dark:bg-graphite-800">
              <div
                className="h-2 rounded-full bg-gradient-to-r from-signal-500 to-signal-400"
                style={{ width: `${step.progress}%` }}
              />
            </div>
          </div>
        ))}
      </div>
    </section>
  );
});

ProgressPanel.displayName = "ProgressPanel";

export default ProgressPanel;
