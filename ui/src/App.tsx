import { useCallback, useEffect, useMemo, useState } from "react";
import ChatPanel from "./components/ChatPanel";
import GraphsPanel from "./components/GraphsPanel";
import LlmSettings from "./components/LlmSettings";
import MdViewer from "./components/MdViewer";
import ModuleScope from "./components/ModuleScope";
import ProgressPanel from "./components/ProgressPanel";
import RepoInput from "./components/RepoInput";
import TopBar from "./components/TopBar";
import { progressSteps as initialSteps } from "./data/mock";

const App = () => {
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [repoUrl, setRepoUrl] = useState("https://github.com/your-org/analytics-repo");
  const [moduleCount, setModuleCount] = useState(48);
  const [scanDepth, setScanDepth] = useState(3);
  const [steps, setSteps] = useState(initialSteps);

  useEffect(() => {
    const stored = window.localStorage.getItem("cartography-theme");
    if (stored === "light" || stored === "dark") {
      setTheme(stored);
    }
  }, []);

  useEffect(() => {
    document.documentElement.classList.toggle("dark", theme === "dark");
    window.localStorage.setItem("cartography-theme", theme);
  }, [theme]);

  useEffect(() => {
    const interval = window.setInterval(() => {
      setSteps((prev) =>
        prev.map((step) => {
          const variance = Math.random() * 6 - 3;
          const next = Math.max(12, Math.min(100, step.progress + variance));
          return { ...step, progress: Math.round(next) };
        })
      );
    }, 2200);
    return () => window.clearInterval(interval);
  }, []);

  const overallProgress = useMemo(
    () => Math.round(steps.reduce((acc, step) => acc + step.progress, 0) / steps.length),
    [steps]
  );

  const handleAnalyze = useCallback(() => {
    setSteps((prev) => prev.map((step) => ({ ...step, progress: Math.min(100, step.progress + 8) })));
  }, []);

  return (
    <div className="min-h-screen bg-graphite-50 bg-grid bg-[length:24px_24px] px-4 py-6 text-graphite-900 dark:bg-graphite-900 dark:text-graphite-50">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <TopBar theme={theme} onToggleTheme={() => setTheme(theme === "dark" ? "light" : "dark")} />

        <div className="grid gap-6 lg:grid-cols-[1.15fr_0.85fr]">
          <div className="space-y-6">
            <RepoInput repoUrl={repoUrl} onChange={setRepoUrl} onAnalyze={handleAnalyze} />
            <div className="grid gap-6 md:grid-cols-2">
              <ProgressPanel steps={steps} overall={overallProgress} />
              <ModuleScope
                moduleCount={moduleCount}
                scanDepth={scanDepth}
                onModuleCountChange={setModuleCount}
                onScanDepthChange={setScanDepth}
              />
            </div>
            <GraphsPanel />
          </div>

          <div className="grid gap-6">
            <ChatPanel />
            <MdViewer />
            <LlmSettings />
          </div>
        </div>
      </div>
    </div>
  );
};

export default App;
