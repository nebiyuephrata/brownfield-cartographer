import { useCallback, useEffect, useMemo, useState } from "react";
import { api } from "./api/cartography";
import ChatPanel from "./components/ChatPanel";
import GraphsPanel from "./components/GraphsPanel";
import LlmSettings from "./components/LlmSettings";
import MdViewer from "./components/MdViewer";
import ModuleScope from "./components/ModuleScope";
import ProgressPanel from "./components/ProgressPanel";
import RepoInput from "./components/RepoInput";
import TopBar from "./components/TopBar";
import { progressSteps as initialSteps } from "./data/mock";
import type { GraphPayload, ProgressStep } from "./api/cartography";
import { deriveGraphSummary } from "./api/helpers";
import type { LlmProvider } from "./data/providers";

const App = () => {
  const [theme, setTheme] = useState<"light" | "dark">("dark");
  const [repoUrl, setRepoUrl] = useState("https://github.com/your-org/analytics-repo");
  const [moduleCount, setModuleCount] = useState(48);
  const [scanDepth, setScanDepth] = useState(3);
  const [steps, setSteps] = useState<ProgressStep[]>(initialSteps);
  const [outputDir, setOutputDir] = useState<string | null>(null);
  const [resolvedRepoPath, setResolvedRepoPath] = useState<string | null>(null);
  const [moduleGraph, setModuleGraph] = useState<GraphPayload | null>(null);
  const [lineageGraph, setLineageGraph] = useState<GraphPayload | null>(null);
  const [statusMessage, setStatusMessage] = useState<string | null>(null);
  const [llmConfig, setLlmConfig] = useState({
    provider: "ollama" as LlmProvider,
    model: "llama3.1",
    fallbackProvider: "openai" as LlmProvider,
    fallbackModel: "gpt-4.1-mini",
    quotaDepleted: false,
    apiKey: "",
    baseUrl: "http://localhost:11434"
  });

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
    if (!outputDir) return;
    const interval = window.setInterval(async () => {
      try {
        const progress = await api.progress(outputDir);
        setSteps(progress.steps);
      } catch {
        // keep last known steps on errors
      }
    }, 2200);
    return () => window.clearInterval(interval);
  }, [outputDir]);

  useEffect(() => {
    if (!outputDir) return;
    const fetchGraphs = async () => {
      try {
        const [module, lineage] = await Promise.all([api.moduleGraph(outputDir), api.lineageGraph(outputDir)]);
        setModuleGraph(module);
        setLineageGraph(lineage);
      } catch {
        // ignore for now
      }
    };
    void fetchGraphs();
  }, [outputDir]);

  const overallProgress = useMemo(
    () => Math.round(steps.reduce((acc, step) => acc + step.progress, 0) / steps.length),
    [steps]
  );

  const handleAnalyze = useCallback(async () => {
    setStatusMessage(null);
    try {
      const response = await api.analyze({ repo_path: repoUrl, output_dir: ".cartography" });
      setOutputDir(response.output_dir);
      setResolvedRepoPath(response.repo_path);
      setStatusMessage(`Analysis complete for ${response.repo_path}`);
      setSteps((prev) => prev.map((step) => ({ ...step, progress: 100 })));
      const [module, lineage] = await Promise.all([
        api.moduleGraph(response.output_dir),
        api.lineageGraph(response.output_dir)
      ]);
      setModuleGraph(module);
      setLineageGraph(lineage);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Failed to run analysis.");
    }
  }, [repoUrl]);

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
            <GraphsPanel moduleGraph={moduleGraph} lineageGraph={lineageGraph} />
          </div>

          <div className="grid gap-6">
            <ChatPanel outputDir={outputDir} llmConfig={llmConfig} />
            <MdViewer repoPath={resolvedRepoPath ?? repoUrl} outputDir={outputDir} />
            <LlmSettings
              provider={llmConfig.provider}
              model={llmConfig.model}
              fallbackProvider={llmConfig.fallbackProvider}
              fallbackModel={llmConfig.fallbackModel}
              quotaDepleted={llmConfig.quotaDepleted}
              apiKey={llmConfig.apiKey}
              baseUrl={llmConfig.baseUrl}
              onChange={(next) => setLlmConfig((prev) => ({ ...prev, ...next }))}\n            />
          </div>
        </div>
        {statusMessage ? (
          <div className="rounded-2xl bg-white/80 px-5 py-3 text-xs text-graphite-600 shadow-sm dark:bg-graphite-900/60 dark:text-graphite-200">
            {statusMessage} · Graphs: {deriveGraphSummary(moduleGraph).nodes} nodes / {deriveGraphSummary(moduleGraph).edges} edges
          </div>
        ) : null}
      </div>
    </div>
  );
};

export default App;
