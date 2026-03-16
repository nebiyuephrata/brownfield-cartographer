import { memo, useCallback, useMemo, useState } from "react";
import { api } from "../api/cartography";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
  source?: "llm" | "heuristic";
}

const initialMessages: Message[] = [
  {
    id: "m1",
    role: "assistant",
    content: "Ask about blast radius, ownership gaps, or onboarding steps.",
    source: "heuristic"
  },
  {
    id: "m2",
    role: "assistant",
    content: "I can summarize the impact of changing staging models in the last 24 hours.",
    source: "heuristic"
  }
];

interface ChatPanelProps {
  outputDir?: string | null;
  repoPath?: string | null;
  llmConfig: {
    provider: string;
    model: string;
    fallbackProvider: string;
    fallbackModel: string;
    apiKey: string;
    baseUrl: string;
    quotaDepleted: boolean;
  };
}

const ChatPanel = memo(({ outputDir, repoPath, llmConfig }: ChatPanelProps) => {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);
  const [llmCount, setLlmCount] = useState(0);
  const [heuristicCount, setHeuristicCount] = useState(0);

  const visibleMessages = useMemo(() => messages.slice(-8), [messages]);

  const handleSend = useCallback(() => {
    if (!input.trim() || isSending) return;
    const userMessage: Message = {
      id: `u-${Date.now()}`,
      role: "user",
      content: input.trim()
    };
    setMessages((prev) => [...prev, userMessage]);
    setInput("");
    setIsSending(true);

    const submit = async () => {
      try {
        if (!outputDir) {
          throw new Error("Run analysis first to enable chat insights.");
        }
        const question = userMessage.content.toLowerCase();
        const heuristicTokens = ["blast", "impact", "critical", "ingestion", "source", "logic", "active"];
        const shouldUseHeuristics = heuristicTokens.some((token) => question.includes(token));

        if (shouldUseHeuristics) {
          const insights = await api.dayOne(outputDir);
          let answer = "";
          if (question.includes("blast") || question.includes("impact")) {
            answer = insights.blast_radius;
          } else if (question.includes("critical")) {
            answer = insights.critical_datasets;
          } else if (question.includes("ingestion") || question.includes("source")) {
            answer = insights.main_ingestion_path;
          } else if (question.includes("logic")) {
            answer = insights.business_logic_locations;
          } else if (question.includes("active")) {
            answer = insights.most_active_files;
          } else {
            answer = [
              insights.main_ingestion_path,
              insights.critical_datasets,
              insights.blast_radius,
              insights.business_logic_locations,
              insights.most_active_files
            ].join(" ");
          }
          const assistantMessage: Message = {
            id: `a-${Date.now()}`,
            role: "assistant",
            content: `${answer}\n\n(Answer generated without LLM to save cost.)`,
            source: "heuristic"
          };
          setMessages((prev) => [...prev, assistantMessage]);
          setHeuristicCount((prev) => prev + 1);
          return;
        }

        const response = await api.chat({
          question: userMessage.content,
          output_dir: outputDir,
          repo_path: repoPath ?? undefined,
          top_k: 6,
          provider: llmConfig.provider,
          model: llmConfig.model,
          fallback_provider: llmConfig.fallbackProvider,
          fallback_model: llmConfig.fallbackModel,
          api_key: llmConfig.apiKey,
          fallback_api_key: llmConfig.apiKey,
          base_url: llmConfig.baseUrl,
          quota_depleted: llmConfig.quotaDepleted
        });
        const sourceText =
          response.sources && response.sources.length > 0
            ? `\n\nSources:\n${response.sources.slice(0, 4).join("\n")}`
            : "";
        const assistantMessage: Message = {
          id: `a-${Date.now()}`,
          role: "assistant",
          content: `${response.answer}${sourceText}`,
          source: "llm"
        };
        setMessages((prev) => [...prev, assistantMessage]);
        setLlmCount((prev) => prev + 1);
      } catch (error) {
        const assistantMessage: Message = {
          id: `a-${Date.now()}`,
          role: "assistant",
          content: error instanceof Error ? error.message : "Unable to reach the analysis service.",
          source: "heuristic"
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } finally {
        setIsSending(false);
      }
    };

    void submit();
  }, [input, isSending, outputDir, repoPath, llmConfig]);

  return (
    <section className="glass flex h-full flex-col rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-graphite-700 dark:text-graphite-100">Ask the codebase</h2>
          <p className="text-xs text-graphite-500 dark:text-graphite-300">Conversational insights with blast radius context.</p>
        </div>
        <span className="rounded-full border border-graphite-200 px-3 py-1 text-xs text-graphite-600 dark:border-graphite-700 dark:text-graphite-200">
          LLM: {llmConfig.quotaDepleted ? llmConfig.fallbackProvider : llmConfig.provider} /{" "}
          {llmConfig.quotaDepleted ? llmConfig.fallbackModel : llmConfig.model}
        </span>
      </div>
      <div className="mt-3 flex flex-wrap items-center gap-2 text-[11px] text-graphite-500 dark:text-graphite-300">
        <span className="rounded-full border border-graphite-200 px-3 py-1 dark:border-graphite-700">
          LLM calls: {llmCount}
        </span>
        <span className="rounded-full border border-graphite-200 px-3 py-1 dark:border-graphite-700">
          Heuristic answers: {heuristicCount}
        </span>
      </div>
      <div className="mt-4 flex-1 space-y-3 overflow-y-auto pr-2 scrollbar-hidden">
        {visibleMessages.map((message) => (
          <div
            key={message.id}
            className={`rounded-2xl px-4 py-3 text-xs shadow-sm ${
              message.role === "user"
                ? "ml-auto w-4/5 bg-graphite-900 text-white"
                : "w-4/5 bg-white/80 text-graphite-700 dark:bg-graphite-900/70 dark:text-graphite-100"
            }`}
          >
            {message.content}
            {message.role === "assistant" && message.source ? (
              <div className="mt-2 text-[10px] uppercase tracking-[0.2em] text-graphite-400">
                {message.source}
              </div>
            ) : null}
          </div>
        ))}
      </div>
      <div className="mt-3 flex flex-wrap gap-2 text-[11px] text-graphite-500 dark:text-graphite-300">
        {[
          "What is the blast radius?",
          "Which datasets are critical?",
          "Where is the main ingestion path?",
          "Which modules have heavy business logic?"
        ].map((suggestion) => (
          <button
            key={suggestion}
            onClick={() => setInput(suggestion)}
            className="rounded-full border border-graphite-200 px-3 py-1 hover:border-signal-500 dark:border-graphite-700"
          >
            {suggestion}
          </button>
        ))}
      </div>
      <div className="mt-4 flex gap-2">
        <input
          value={input}
          onChange={(event) => setInput(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter") {
              handleSend();
            }
          }}
          placeholder="Ask about blast radius, owners, or missing tests..."
          className="flex-1 rounded-xl border border-graphite-200 bg-white/80 px-3 py-2 text-xs text-graphite-800 shadow-sm outline-none focus:border-signal-500 dark:border-graphite-700 dark:bg-graphite-900/60 dark:text-graphite-100"
        />
        <button
          onClick={handleSend}
          disabled={isSending}
          className="rounded-xl bg-signal-500 px-4 py-2 text-xs font-semibold text-graphite-900 transition hover:translate-y-[-1px]"
        >
          {isSending ? "Sending..." : "Send"}
        </button>
      </div>
    </section>
  );
});

ChatPanel.displayName = "ChatPanel";

export default ChatPanel;
