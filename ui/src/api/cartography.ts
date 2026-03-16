export const apiBaseUrl = (import.meta.env.VITE_API_BASE_URL as string) || "http://localhost:8000";

export interface ProgressStep {
  id: string;
  label: string;
  progress: number;
}

export interface ProgressResponse {
  steps: ProgressStep[];
  overall: number;
  last_event?: string | null;
}

export interface AnalyzeResponse {
  status: string;
  repo_path: string;
  output_dir: string;
  module_nodes: number;
  module_edges: number;
  lineage_nodes: number;
  lineage_edges: number;
}

export interface GraphPayload {
  nodes: Array<{ id: string; [key: string]: unknown }>;
  edges: Array<{ source: string; target: string; [key: string]: unknown }>;
}

export interface MarkdownResponse {
  content: string;
}

export interface DayOneInsights {
  main_ingestion_path: string;
  critical_datasets: string;
  blast_radius: string;
  business_logic_locations: string;
  most_active_files: string;
}

export interface ChatResponse {
  answer: string;
  hints: string[];
}

async function fetchJson<T>(path: string, options?: RequestInit): Promise<T> {
  const response = await fetch(`${apiBaseUrl}${path}`, {
    headers: { "Content-Type": "application/json" },
    ...options
  });
  if (!response.ok) {
    const text = await response.text();
    throw new Error(text || `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export const api = {
  analyze: (payload: { repo_path: string; output_dir?: string; run_lineage?: boolean; run_semantic?: boolean }) =>
    fetchJson<AnalyzeResponse>("/analyze", {
      method: "POST",
      body: JSON.stringify(payload)
    }),
  progress: (outputDir: string) =>
    fetchJson<ProgressResponse>(`/progress?output_dir=${encodeURIComponent(outputDir)}`),
  moduleGraph: (outputDir: string) =>
    fetchJson<GraphPayload>(`/graphs/module?output_dir=${encodeURIComponent(outputDir)}`),
  lineageGraph: (outputDir: string) =>
    fetchJson<GraphPayload>(`/graphs/lineage?output_dir=${encodeURIComponent(outputDir)}`),
  readme: (repoPath: string) =>
    fetchJson<MarkdownResponse>(`/markdown/readme?repo_path=${encodeURIComponent(repoPath)}`),
  onboarding: (outputDir: string) =>
    fetchJson<MarkdownResponse>(`/markdown/onboarding?output_dir=${encodeURIComponent(outputDir)}`),
  dayOne: (outputDir: string) =>
    fetchJson<DayOneInsights>(`/insights/day-one?output_dir=${encodeURIComponent(outputDir)}`),
  chat: (payload: { question: string; output_dir: string }) =>
    fetchJson<ChatResponse>("/chat", {
      method: "POST",
      body: JSON.stringify(payload)
    })
};
