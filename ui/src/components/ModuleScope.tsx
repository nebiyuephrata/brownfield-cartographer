import { memo } from "react";

interface ModuleScopeProps {
  moduleCount: number;
  scanDepth: number;
  onModuleCountChange: (value: number) => void;
  onScanDepthChange: (value: number) => void;
}

const ModuleScope = memo(
  ({ moduleCount, scanDepth, onModuleCountChange, onScanDepthChange }: ModuleScopeProps) => {
    return (
      <section className="glass rounded-2xl p-5">
        <h2 className="text-sm font-semibold text-graphite-700 dark:text-graphite-100">Scan scope</h2>
        <p className="mt-1 text-xs text-graphite-500 dark:text-graphite-300">
          Control how many modules and dependency levels to include in the analysis.
        </p>
        <div className="mt-4 space-y-4">
          <label className="flex flex-col gap-2 text-xs text-graphite-600 dark:text-graphite-200">
            Modules to scan: <span className="font-semibold text-graphite-900 dark:text-white">{moduleCount}</span>
            <input
              type="range"
              min={5}
              max={200}
              value={moduleCount}
              onChange={(event) => onModuleCountChange(Number(event.target.value))}
              className="accent-signal-500"
            />
          </label>
          <label className="flex flex-col gap-2 text-xs text-graphite-600 dark:text-graphite-200">
            Dependency depth: <span className="font-semibold text-graphite-900 dark:text-white">{scanDepth}</span>
            <input
              type="range"
              min={1}
              max={6}
              value={scanDepth}
              onChange={(event) => onScanDepthChange(Number(event.target.value))}
              className="accent-signal-500"
            />
          </label>
        </div>
      </section>
    );
  }
);

ModuleScope.displayName = "ModuleScope";

export default ModuleScope;
