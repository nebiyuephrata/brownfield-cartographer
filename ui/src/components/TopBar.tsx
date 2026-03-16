import { memo } from "react";

interface TopBarProps {
  theme: "light" | "dark";
  onToggleTheme: () => void;
  statusLabel: string;
}

const TopBar = memo(({ theme, onToggleTheme, statusLabel }: TopBarProps) => {
  return (
    <header className="flex flex-wrap items-center justify-between gap-4 rounded-3xl bg-white/70 p-6 shadow-soft backdrop-blur dark:bg-graphite-800/70">
      <div>
        <p className="text-xs uppercase tracking-[0.2em] text-graphite-500 dark:text-graphite-300">
          Brownfield Cartographer
        </p>
        <h1 className="font-display text-3xl font-semibold text-graphite-900 dark:text-white">
          <span className="text-gradient">Live Intelligence</span> for your data stack
        </h1>
        <p className="mt-2 max-w-2xl text-sm text-graphite-600 dark:text-graphite-200">
          Track repository analysis, dependency blast radius, and LLM-powered insights in one responsive workspace.
        </p>
      </div>
      <div className="flex items-center gap-3">
        <div className="rounded-full border border-graphite-200 bg-white/80 px-3 py-2 text-xs text-graphite-700 dark:border-graphite-700 dark:bg-graphite-900/60 dark:text-graphite-200">
          Status: <span className="font-semibold text-signal-600">{statusLabel || "Idle"}</span>
        </div>
        <button
          className="rounded-full border border-graphite-200 bg-white/80 px-4 py-2 text-sm font-medium text-graphite-700 transition hover:border-signal-500 hover:text-graphite-900 dark:border-graphite-700 dark:bg-graphite-900/60 dark:text-graphite-200"
          onClick={onToggleTheme}
        >
          {theme === "dark" ? "Light" : "Dark"} mode
        </button>
      </div>
    </header>
  );
});

TopBar.displayName = "TopBar";

export default TopBar;
