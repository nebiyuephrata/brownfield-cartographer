import { memo, useCallback, useMemo, useState } from "react";
import clsx from "clsx";
import { LlmProvider, providerLabels, providerModels } from "../data/providers";

const LlmSettings = memo(() => {
  const [provider, setProvider] = useState<LlmProvider>("ollama");
  const [model, setModel] = useState("llama3.1");
  const [fallbackProvider, setFallbackProvider] = useState<LlmProvider>("openai");
  const [fallbackModel, setFallbackModel] = useState("gpt-4.1-mini");
  const [quotaDepleted, setQuotaDepleted] = useState(false);
  const [apiKey, setApiKey] = useState("");
  const [baseUrl, setBaseUrl] = useState("http://localhost:11434");

  const availableModels = useMemo(() => providerModels[provider], [provider]);
  const availableFallbackModels = useMemo(() => providerModels[fallbackProvider], [fallbackProvider]);

  const effectiveProvider = quotaDepleted ? fallbackProvider : provider;
  const effectiveModel = quotaDepleted ? fallbackModel : model;

  const envPreview = useMemo(() => {
    return [
      `VITE_LLM_PROVIDER=${provider}`,
      `VITE_LLM_MODEL=${model}`,
      `VITE_LLM_FALLBACK_PROVIDER=${fallbackProvider}`,
      `VITE_LLM_FALLBACK_MODEL=${fallbackModel}`,
      `VITE_LLM_BASE_URL=${baseUrl}`,
      `VITE_LLM_API_KEY=${apiKey || "your_api_key_here"}`
    ].join("\n");
  }, [provider, model, fallbackProvider, fallbackModel, baseUrl, apiKey]);

  const handleCopyEnv = useCallback(async () => {
    await navigator.clipboard.writeText(envPreview);
  }, [envPreview]);

  return (
    <section className="glass rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-graphite-700 dark:text-graphite-100">LLM routing</h2>
          <p className="text-xs text-graphite-500 dark:text-graphite-300">
            Configure provider, models, and seamless fallback when quota runs out.
          </p>
        </div>
        <span className="rounded-full bg-signal-500/20 px-3 py-1 text-xs font-semibold text-signal-600">
          Active: {providerLabels[effectiveProvider]}
        </span>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div className="space-y-3">
          <label className="text-xs font-semibold text-graphite-600 dark:text-graphite-300">Primary provider</label>
          <select
            value={provider}
            onChange={(event) => {
              const value = event.target.value as LlmProvider;
              setProvider(value);
              setModel(providerModels[value][0]);
            }}
            className="w-full rounded-xl border border-graphite-200 bg-white/80 px-3 py-2 text-xs text-graphite-700 dark:border-graphite-700 dark:bg-graphite-900/60 dark:text-graphite-100"
          >
            {Object.entries(providerLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <label className="text-xs font-semibold text-graphite-600 dark:text-graphite-300">Primary model</label>
          <select
            value={model}
            onChange={(event) => setModel(event.target.value)}
            className="w-full rounded-xl border border-graphite-200 bg-white/80 px-3 py-2 text-xs text-graphite-700 dark:border-graphite-700 dark:bg-graphite-900/60 dark:text-graphite-100"
          >
            {availableModels.map((entry) => (
              <option key={entry} value={entry}>
                {entry}
              </option>
            ))}
          </select>
        </div>
        <div className="space-y-3">
          <label className="text-xs font-semibold text-graphite-600 dark:text-graphite-300">Fallback provider</label>
          <select
            value={fallbackProvider}
            onChange={(event) => {
              const value = event.target.value as LlmProvider;
              setFallbackProvider(value);
              setFallbackModel(providerModels[value][0]);
            }}
            className="w-full rounded-xl border border-graphite-200 bg-white/80 px-3 py-2 text-xs text-graphite-700 dark:border-graphite-700 dark:bg-graphite-900/60 dark:text-graphite-100"
          >
            {Object.entries(providerLabels).map(([value, label]) => (
              <option key={value} value={value}>
                {label}
              </option>
            ))}
          </select>
          <label className="text-xs font-semibold text-graphite-600 dark:text-graphite-300">Fallback model</label>
          <select
            value={fallbackModel}
            onChange={(event) => setFallbackModel(event.target.value)}
            className="w-full rounded-xl border border-graphite-200 bg-white/80 px-3 py-2 text-xs text-graphite-700 dark:border-graphite-700 dark:bg-graphite-900/60 dark:text-graphite-100"
          >
            {availableFallbackModels.map((entry) => (
              <option key={entry} value={entry}>
                {entry}
              </option>
            ))}
          </select>
        </div>
      </div>
      <div className="mt-4 grid gap-4 md:grid-cols-2">
        <div className="space-y-3">
          <label className="text-xs font-semibold text-graphite-600 dark:text-graphite-300">API key</label>
          <input
            value={apiKey}
            onChange={(event) => setApiKey(event.target.value)}
            placeholder="sk-..."
            className="w-full rounded-xl border border-graphite-200 bg-white/80 px-3 py-2 text-xs text-graphite-700 dark:border-graphite-700 dark:bg-graphite-900/60 dark:text-graphite-100"
          />
        </div>
        <div className="space-y-3">
          <label className="text-xs font-semibold text-graphite-600 dark:text-graphite-300">Base URL (local Ollama)</label>
          <input
            value={baseUrl}
            onChange={(event) => setBaseUrl(event.target.value)}
            placeholder="http://localhost:11434"
            className="w-full rounded-xl border border-graphite-200 bg-white/80 px-3 py-2 text-xs text-graphite-700 dark:border-graphite-700 dark:bg-graphite-900/60 dark:text-graphite-100"
          />
        </div>
      </div>
      <div className="mt-4 flex flex-wrap items-center gap-3">
        <button
          onClick={() => setQuotaDepleted((prev) => !prev)}
          className={clsx(
            "rounded-full px-4 py-2 text-xs font-semibold",
            quotaDepleted
              ? "bg-graphite-900 text-white"
              : "border border-graphite-200 text-graphite-600 dark:border-graphite-700 dark:text-graphite-200"
          )}
        >
          {quotaDepleted ? "Quota depleted" : "Quota healthy"}
        </button>
        <div className="text-xs text-graphite-600 dark:text-graphite-300">
          Effective route: <span className="font-semibold text-graphite-900 dark:text-white">{effectiveProvider}</span> / {" "}
          <span className="font-semibold text-graphite-900 dark:text-white">{effectiveModel}</span>
        </div>
      </div>
      <div className="mt-4 rounded-2xl bg-graphite-900 p-3 text-[11px] text-graphite-100 dark:bg-graphite-950">
        <pre className="whitespace-pre-wrap">{envPreview}</pre>
      </div>
      <div className="mt-3 flex items-center gap-3 text-xs text-graphite-500 dark:text-graphite-300">
        <button
          onClick={handleCopyEnv}
          className="rounded-full border border-graphite-200 px-3 py-1 text-xs font-semibold text-graphite-600 dark:border-graphite-700 dark:text-graphite-200"
        >
          Copy .env block
        </button>
        <span>Front-end config is for local dev only; secure storage belongs on the backend.</span>
      </div>
    </section>
  );
});

LlmSettings.displayName = "LlmSettings";

export default LlmSettings;
