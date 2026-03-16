import { useCallback, useEffect, useMemo, useState } from "react";
import { api, apiBaseUrl } from "./api/cartography";
import ChatPanel from "./components/ChatPanel";
import GraphsPanel from "./components/GraphsPanel";
import LlmSettings from "./components/LlmSettings";
import MdViewer from "./components/MdViewer";
import ModuleScope from "./components/ModuleScope";
import ProgressPanel from "./components/ProgressPanel";
import RepoInput from "./components/RepoInput";
import TopBar from "./components/TopBar";
import { progressSteps as initialSteps } from "./data/mock";
import type { GraphPayload, ProgressStep, RunResponse } from "./api/cartography";
import { deriveGraphSummary } from "./api/helpers";
import type { LlmProvider } from "./data/providers";
import RunHistory from "./components/RunHistory";
import RunDetail from "./components/RunDetail";
import BlastRadiusPanel from "./components/BlastRadiusPanel";
import Toast, { ToastItem } from "./components/Toast";
import ErrorLogPanel from "./components/ErrorLogPanel";

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
  const [statusLabel, setStatusLabel] = useState("Idle");
  const [activeRunId, setActiveRunId] = useState<string | null>(null);
  const [runHistory, setRunHistory] = useState<RunResponse[]>([]);
  const [selectedRun, setSelectedRun] = useState<RunResponse | null>(null);
  const [indexStatus, setIndexStatus] = useState<string | null>(null);
  const [isRunning, setIsRunning] = useState(false);
  const [focusLineageNodeId, setFocusLineageNodeId] = useState<string | null>(null);
  const [toasts, setToasts] = useState<ToastItem[]>([]);
  const [errorLog, setErrorLog] = useState<ToastItem[]>([]);

  const pushToast = useCallback((message: string, tone: ToastItem["tone"] = "error") => {
    const id = `toast-${Date.now()}-${Math.random().toString(36).slice(2, 6)}`;
    const item: ToastItem = { id, message, tone };
    setToasts((prev) => [...prev, item]);
    if (tone === "error") {
      setErrorLog((prev) => [...prev, item]);
    }
    window.setTimeout(() => {
      setToasts((prev) => prev.filter((toast) => toast.id !== id));
    }, 4000);
  }, []);
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
        if (progress.last_event) {
          setStatusLabel(progress.last_event.replace(/_/g, " "));
        }
      } catch {
        // keep last known steps on errors
      }
    }, 2200);
    return () => window.clearInterval(interval);
  }, [outputDir]);

  useEffect(() => {
    if (!outputDir) return;
    const refreshHistory = async () => {
      try {
        const response = await api.listRuns(outputDir);
        setRunHistory(response.runs);
      } catch {
        // ignore
      }
    };
    void refreshHistory();
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
      setStatusLabel("Queued");
      setIsRunning(true);
      const run = await api.startRun({ repo_path: repoUrl, output_dir: ".cartography", enable_index: false });
      setActiveRunId(run.run_id);
      setSelectedRun(run);
      setOutputDir(run.output_dir);
      setResolvedRepoPath(run.repo_path);
      setStatusMessage(`Run started for ${run.repo_path}`);
      setRunHistory((prev) => [...prev, run]);

      const events = new EventSource(`${apiBaseUrl}/runs/${run.run_id}/events`);
      events.addEventListener("status", (event) => {
        try {
          const payload = JSON.parse((event as MessageEvent).data);
          setStatusLabel(payload.status ?? "Running");
          if (payload.status === "complete") {
            setIsRunning(false);
            void api.listRuns(run.output_dir).then((response) => setRunHistory(response.runs));
          }
        } catch {
          // ignore
        }
      });
      events.addEventListener("trace", () => {
        setStatusLabel("Running");
      });
      events.onerror = () => {
        events.close();
      };

      const waitForComplete = async () => {
        while (true) {
          try {
            const response = await api.listRuns(run.output_dir);
            setRunHistory(response.runs);
            const current = response.runs.find((entry) => entry.run_id === run.run_id);
            if (current?.status === "complete") {
              setSelectedRun(current);
              const [module, lineage] = await Promise.all([
                api.moduleGraph(run.output_dir),
                api.lineageGraph(run.output_dir)
              ]);
              setModuleGraph(module);
              setLineageGraph(lineage);
              setStatusMessage(`Analysis complete for ${run.repo_path}`);
              setStatusLabel("Complete");
              setIsRunning(false);
              pushToast("Analysis complete.", "success");
              break;
            }
            if (current?.status === "failed") {
              setSelectedRun(current);
              setStatusMessage(current.error ?? "Run failed.");
              setStatusLabel("Failed");
              setIsRunning(false);
              pushToast(current.error ?? "Run failed.");
              break;
            }
          } catch {
            break;
          }
          await new Promise((resolve) => setTimeout(resolve, 2000));
        }
      };
      void waitForComplete();
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Failed to run analysis.");
      setStatusLabel("Failed");
      setIsRunning(false);
      pushToast(error instanceof Error ? error.message : "Failed to run analysis.");
    }
  }, [repoUrl]);

  const handleSelectRun = useCallback((run: RunResponse) => {
    setSelectedRun(run);
    setActiveRunId(run.run_id);
    setOutputDir(run.output_dir);
    setResolvedRepoPath(run.repo_path);
    setStatusLabel(run.status);
  }, []);

  const handleLoadRunGraphs = useCallback(async () => {
    if (!selectedRun) return;
    try {
      const [module, lineage] = await Promise.all([
        api.moduleGraph(selectedRun.output_dir),
        api.lineageGraph(selectedRun.output_dir)
      ]);
      setModuleGraph(module);
      setLineageGraph(lineage);
      setStatusMessage(`Loaded graphs for ${selectedRun.repo_path}`);
    } catch (error) {
      setStatusMessage(error instanceof Error ? error.message : "Failed to load run graphs.");
      pushToast(error instanceof Error ? error.message : "Failed to load run graphs.");
    }
  }, [selectedRun]);

  const handleIndexRepo = useCallback(async () => {
    if (!selectedRun) return;
    setIndexStatus("Indexing repository...");
    try {
      const response = await api.indexRepo({ repo_path: selectedRun.repo_path });
      setIndexStatus(`Indexed ${response.indexed_chunks} chunks.`);
      pushToast(`Indexed ${response.indexed_chunks} chunks.`, "success");
    } catch (error) {
      setIndexStatus(error instanceof Error ? error.message : "Indexing failed.");
      pushToast(error instanceof Error ? error.message : "Indexing failed.");
    }
  }, [selectedRun]);

  return (
    <div className="min-h-screen bg-graphite-50 bg-grid bg-[length:24px_24px] px-4 py-6 text-graphite-900 dark:bg-graphite-900 dark:text-graphite-50">
      <div className="mx-auto flex max-w-7xl flex-col gap-6">
        <TopBar
          theme={theme}
          statusLabel={statusLabel || "Idle"}
          onToggleTheme={() => setTheme(theme === "dark" ? "light" : "dark")}
        />

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
            <GraphsPanel
              moduleGraph={moduleGraph}
              lineageGraph={lineageGraph}
              focusLineageNodeId={focusLineageNodeId}
            />
            <BlastRadiusPanel
              lineageGraph={lineageGraph}
              onSelectNode={(nodeId) => setFocusLineageNodeId(nodeId)}
            />
          </div>

          <div className="grid gap-6">
            <ChatPanel
              outputDir={outputDir}
              repoPath={resolvedRepoPath ?? repoUrl}
              llmConfig={llmConfig}
              onError={(message) => pushToast(message)}
            />
            <MdViewer
              repoPath={resolvedRepoPath ?? repoUrl}
              outputDir={outputDir}
              onError={(message) => pushToast(message)}
            />
            <RunHistory runs={runHistory} activeRunId={activeRunId} onSelect={handleSelectRun} />
            <RunDetail
              run={selectedRun}
              moduleCount={moduleGraph?.nodes?.length ?? 0}
              lineageCount={lineageGraph?.nodes?.length ?? 0}
              onLoadGraphs={handleLoadRunGraphs}
              onIndex={handleIndexRepo}
              indexStatus={indexStatus}
            />
            <ErrorLogPanel logs={errorLog} />
            <LlmSettings
              provider={llmConfig.provider}
              model={llmConfig.model}
              fallbackProvider={llmConfig.fallbackProvider}
              fallbackModel={llmConfig.fallbackModel}
              quotaDepleted={llmConfig.quotaDepleted}
              apiKey={llmConfig.apiKey}
              baseUrl={llmConfig.baseUrl}
              onChange={(next) => setLlmConfig((prev) => ({ ...prev, ...next }))}
            />
          </div>
        </div>
        {statusMessage ? (
          <div className="rounded-2xl bg-white/80 px-5 py-3 text-xs text-graphite-600 shadow-sm dark:bg-graphite-900/60 dark:text-graphite-200">
            {statusMessage} · Graphs: {deriveGraphSummary(moduleGraph).nodes} nodes / {deriveGraphSummary(moduleGraph).edges} edges
          </div>
        ) : null}
        {isRunning ? (
          <div className="fixed inset-0 z-[70] flex items-center justify-center bg-graphite-900/70 p-6">
            <div className="flex w-full max-w-sm flex-col items-center gap-3 rounded-3xl bg-white/90 p-6 text-center text-graphite-700 shadow-soft dark:bg-graphite-950 dark:text-graphite-100">
              <div className="h-10 w-10 animate-spin rounded-full border-4 border-graphite-200 border-t-signal-500 dark:border-graphite-700" />
              <div className="text-sm font-semibold">Analyzing repo…</div>
              <div className="text-xs text-graphite-500 dark:text-graphite-300">
                {statusLabel || "Running"} · This can take a few minutes for large repos.
              </div>
            </div>
          </div>
        ) : null}
        <Toast toasts={toasts} onDismiss={(id) => setToasts((prev) => prev.filter((toast) => toast.id !== id))} />
      </div>
    </div>
  );
};

export default App;
