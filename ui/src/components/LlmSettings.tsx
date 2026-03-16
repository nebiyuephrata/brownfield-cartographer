import { memo, useCallback, useMemo, useState } from "react";
import clsx from "clsx";
import { api } from "../api/cartography";
import { LlmProvider, providerLabels, providerModels } from "../data/providers";

interface LlmSettingsProps {
  provider: LlmProvider;
  model: string;
  fallbackProvider: LlmProvider;
  fallbackModel: string;
  quotaDepleted: boolean;
  apiKey: string;
  baseUrl: string;
  onChange: (next: Partial<Omit<LlmSettingsProps, "onChange">>) => void;
}

const LlmSettings = memo(
  ({ provider, model, fallbackProvider, fallbackModel, quotaDepleted, apiKey, baseUrl, onChange }: LlmSettingsProps) => {
    const [saveStatus, setSaveStatus] = useState<string | null>(null);

    const availableModels = useMemo(() => providerModels[provider], [provider]);
    const availableFallbackModels = useMemo(() => providerModels[fallbackProvider], [fallbackProvider]);

    const effectiveProvider = quotaDepleted ? fallbackProvider : provider;
    const effectiveModel = quotaDepleted ? fallbackModel : model;

    const frontendEnvPreview = useMemo(() => {
      return [
        `VITE_LLM_PROVIDER=${provider}`,
        `VITE_LLM_MODEL=${model}`,
        `VITE_LLM_FALLBACK_PROVIDER=${fallbackProvider}`,
        `VITE_LLM_FALLBACK_MODEL=${fallbackModel}`,
        `VITE_LLM_BASE_URL=${baseUrl}`,
        `VITE_LLM_API_KEY=${apiKey || "your_api_key_here"}`
      ].join("\n");
    }, [provider, model, fallbackProvider, fallbackModel, baseUrl, apiKey]);

    const backendEnvPreview = useMemo(() => {
      return [
        `CARTOGRAPHY_LLM_PROVIDER=${provider}`,
        `CARTOGRAPHY_LLM_MODEL=${model}`,
        `CARTOGRAPHY_LLM_FALLBACK_PROVIDER=${fallbackProvider}`,
        `CARTOGRAPHY_LLM_FALLBACK_MODEL=${fallbackModel}`,
        `CARTOGRAPHY_LLM_BASE_URL=${baseUrl}`,
        `CARTOGRAPHY_LLM_API_KEY=${apiKey || "your_api_key_here"}`,
        `CARTOGRAPHY_LLM_FALLBACK_API_KEY=${apiKey || "your_api_key_here"}`
      ].join("\n");
    }, [provider, model, fallbackProvider, fallbackModel, baseUrl, apiKey]);

    const handleCopyEnv = useCallback(async (text: string) => {
      await navigator.clipboard.writeText(text);
    }, []);

    const handleSaveBackendEnv = useCallback(async () => {
      setSaveStatus("Saving to .env...");
      try {
        const values: Record<string, string> = {
          CARTOGRAPHY_LLM_PROVIDER: provider,
          CARTOGRAPHY_LLM_MODEL: model,
          CARTOGRAPHY_LLM_FALLBACK_PROVIDER: fallbackProvider,
          CARTOGRAPHY_LLM_FALLBACK_MODEL: fallbackModel,
          CARTOGRAPHY_LLM_BASE_URL: baseUrl,
          CARTOGRAPHY_LLM_API_KEY: apiKey,
          CARTOGRAPHY_LLM_FALLBACK_API_KEY: apiKey
        };
        if (provider === "ollama") {
          values.OLLAMA_MODEL = model;
          values.OLLAMA_HOST = baseUrl;
        } else if (apiKey) {
          values.OPENROUTER_API_KEY = apiKey;
          values.OPENROUTER_MODEL = model;
        }
        await api.saveEnv({ values });
        setSaveStatus("Saved to backend .env.");
      } catch (error) {
        setSaveStatus(error instanceof Error ? error.message : "Failed to save .env.");
      }
    }, [provider, model, fallbackProvider, fallbackModel, baseUrl, apiKey]);

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
                onChange({ provider: value, model: providerModels[value][0] });
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
              onChange={(event) => onChange({ model: event.target.value })}
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
                onChange({ fallbackProvider: value, fallbackModel: providerModels[value][0] });
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
              onChange={(event) => onChange({ fallbackModel: event.target.value })}
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
              onChange={(event) => onChange({ apiKey: event.target.value })}
              placeholder="sk-..."
              className="w-full rounded-xl border border-graphite-200 bg-white/80 px-3 py-2 text-xs text-graphite-700 dark:border-graphite-700 dark:bg-graphite-900/60 dark:text-graphite-100"
            />
          </div>
          <div className="space-y-3">
            <label className="text-xs font-semibold text-graphite-600 dark:text-graphite-300">Base URL (local Ollama)</label>
            <input
              value={baseUrl}
              onChange={(event) => onChange({ baseUrl: event.target.value })}
              placeholder="http://localhost:11434"
              className="w-full rounded-xl border border-graphite-200 bg-white/80 px-3 py-2 text-xs text-graphite-700 dark:border-graphite-700 dark:bg-graphite-900/60 dark:text-graphite-100"
            />
          </div>
        </div>
        <div className="mt-4 flex flex-wrap items-center gap-3">
          <button
            onClick={() => onChange({ quotaDepleted: !quotaDepleted })}
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
            Effective route: <span className="font-semibold text-graphite-900 dark:text-white">{effectiveProvider}</span> /{" "}
            <span className="font-semibold text-graphite-900 dark:text-white">{effectiveModel}</span>
          </div>
        </div>
        <div className="mt-4 grid gap-3 md:grid-cols-2">
          <div className="rounded-2xl bg-graphite-900 p-3 text-[11px] text-graphite-100 dark:bg-graphite-950">
            <div className="mb-2 text-[10px] uppercase tracking-[0.2em] text-graphite-400">Frontend .env</div>
            <pre className="whitespace-pre-wrap">{frontendEnvPreview}</pre>
          </div>
          <div className="rounded-2xl bg-graphite-900 p-3 text-[11px] text-graphite-100 dark:bg-graphite-950">
            <div className="mb-2 text-[10px] uppercase tracking-[0.2em] text-graphite-400">Backend .env</div>
            <pre className="whitespace-pre-wrap">{backendEnvPreview}</pre>
          </div>
        </div>
        <div className="mt-3 flex flex-wrap items-center gap-3 text-xs text-graphite-500 dark:text-graphite-300">
          <button
            onClick={() => handleCopyEnv(frontendEnvPreview)}
            className="rounded-full border border-graphite-200 px-3 py-1 text-xs font-semibold text-graphite-600 dark:border-graphite-700 dark:text-graphite-200"
          >
            Copy frontend .env
          </button>
          <button
            onClick={() => handleCopyEnv(backendEnvPreview)}
            className="rounded-full border border-graphite-200 px-3 py-1 text-xs font-semibold text-graphite-600 dark:border-graphite-700 dark:text-graphite-200"
          >
            Copy backend .env
          </button>
          <button
            onClick={handleSaveBackendEnv}
            className="rounded-full bg-signal-500 px-3 py-1 text-xs font-semibold text-graphite-900"
          >
            Save backend .env
          </button>
          {saveStatus ? <span>{saveStatus}</span> : null}
        </div>
        <p className="mt-2 text-[11px] text-graphite-500 dark:text-graphite-300">
          Remote providers are routed through OpenRouter in the backend for now.
        </p>
      </section>
    );
  }
);

LlmSettings.displayName = "LlmSettings";

export default LlmSettings;
