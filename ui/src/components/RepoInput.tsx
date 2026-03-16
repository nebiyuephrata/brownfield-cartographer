import { memo } from "react";

interface RepoInputProps {
  repoUrl: string;
  onChange: (value: string) => void;
  onAnalyze: () => void;
}

const RepoInput = memo(({ repoUrl, onChange, onAnalyze }: RepoInputProps) => {
  return (
    <section className="glass rounded-2xl p-5">
      <h2 className="text-sm font-semibold text-graphite-700 dark:text-graphite-100">Target Repository</h2>
      <p className="mt-1 text-xs text-graphite-500 dark:text-graphite-300">
        Connect a GitHub repo to start mapping modules, lineage, and blast radius.
      </p>
      <div className="mt-4 flex flex-col gap-3">
        <input
          value={repoUrl}
          onChange={(event) => onChange(event.target.value)}
          placeholder="https://github.com/org/repo"
          className="w-full rounded-xl border border-graphite-200 bg-white/80 px-4 py-3 text-sm text-graphite-800 shadow-sm outline-none transition focus:border-signal-500 dark:border-graphite-700 dark:bg-graphite-900/60 dark:text-graphite-100"
        />
        <button
          onClick={onAnalyze}
          className="rounded-xl bg-graphite-900 px-4 py-3 text-sm font-semibold text-white transition hover:translate-y-[-1px] hover:bg-graphite-700 dark:bg-signal-600 dark:text-graphite-900"
        >
          Run analysis
        </button>
      </div>
    </section>
  );
});

RepoInput.displayName = "RepoInput";

export default RepoInput;
