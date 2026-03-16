import { memo, useCallback, useMemo, useState } from "react";
import { api } from "../api/cartography";

interface Message {
  id: string;
  role: "user" | "assistant";
  content: string;
}

const initialMessages: Message[] = [
  {
    id: "m1",
    role: "assistant",
    content: "Ask about blast radius, ownership gaps, or onboarding steps."
  },
  {
    id: "m2",
    role: "assistant",
    content: "I can summarize the impact of changing staging models in the last 24 hours."
  }
];

interface ChatPanelProps {
  outputDir?: string | null;
}

const ChatPanel = memo(({ outputDir }: ChatPanelProps) => {
  const [messages, setMessages] = useState<Message[]>(initialMessages);
  const [input, setInput] = useState("");
  const [isSending, setIsSending] = useState(false);

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
        const response = await api.chat({ question: userMessage.content, output_dir: outputDir });
        const assistantMessage: Message = {
          id: `a-${Date.now()}`,
          role: "assistant",
          content: response.answer
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } catch (error) {
        const assistantMessage: Message = {
          id: `a-${Date.now()}`,
          role: "assistant",
          content: error instanceof Error ? error.message : "Unable to reach the analysis service."
        };
        setMessages((prev) => [...prev, assistantMessage]);
      } finally {
        setIsSending(false);
      }
    };

    void submit();
  }, [input, isSending, outputDir]);

  return (
    <section className="glass flex h-full flex-col rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-graphite-700 dark:text-graphite-100">Ask the codebase</h2>
          <p className="text-xs text-graphite-500 dark:text-graphite-300">Conversational insights with blast radius context.</p>
        </div>
        <span className="rounded-full border border-graphite-200 px-3 py-1 text-xs text-graphite-600 dark:border-graphite-700 dark:text-graphite-200">
          LLM: Llama 3.1
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
          </div>
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
