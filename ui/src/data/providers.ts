export type LlmProvider = "ollama" | "openai" | "anthropic" | "google" | "mistral";

export const providerModels: Record<LlmProvider, string[]> = {
  ollama: ["llama3.1", "mistral", "qwen2.5"],
  openai: ["gpt-4.1", "gpt-4.1-mini", "gpt-4o"],
  anthropic: ["claude-3.5-sonnet", "claude-3-haiku"],
  google: ["gemini-1.5-pro", "gemini-1.5-flash"],
  mistral: ["mistral-large", "mixtral-8x7b" ]
};

export const providerLabels: Record<LlmProvider, string> = {
  ollama: "Ollama (Local)",
  openai: "OpenAI",
  anthropic: "Anthropic",
  google: "Google",
  mistral: "Mistral"
};
