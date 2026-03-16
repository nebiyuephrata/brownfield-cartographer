import { memo, useCallback, useMemo, useState } from "react";
import ReactMarkdown from "react-markdown";
import remarkGfm from "remark-gfm";
import { sampleOnboarding, sampleReadme } from "../data/mock";

const MdViewer = memo(() => {
  const [activeTab, setActiveTab] = useState<"readme" | "onboarding">("readme");
  const [content, setContent] = useState({
    readme: sampleReadme,
    onboarding: sampleOnboarding
  });

  const activeContent = useMemo(() => content[activeTab], [content, activeTab]);

  const handleLoadFile = useCallback((event: React.ChangeEvent<HTMLInputElement>) => {
    const file = event.target.files?.[0];
    if (!file) return;
    const reader = new FileReader();
    reader.onload = () => {
      const text = typeof reader.result === "string" ? reader.result : "";
      setContent((prev) => ({ ...prev, [activeTab]: text }));
    };
    reader.readAsText(file);
  }, [activeTab]);

  return (
    <section className="glass flex h-full flex-col rounded-2xl p-5">
      <div className="flex items-center justify-between">
        <div>
          <h2 className="text-sm font-semibold text-graphite-700 dark:text-graphite-100">Markdown viewer</h2>
          <p className="text-xs text-graphite-500 dark:text-graphite-300">Read README and onboarding briefs inline.</p>
        </div>
        <label className="rounded-xl border border-graphite-200 bg-white/80 px-3 py-2 text-xs font-semibold text-graphite-700 hover:border-signal-500 dark:border-graphite-700 dark:bg-graphite-900/60 dark:text-graphite-200">
          Load Markdown
          <input type="file" accept=".md" className="hidden" onChange={handleLoadFile} />
        </label>
      </div>
      <div className="mt-4 flex gap-2">
        <button
          onClick={() => setActiveTab("readme")}
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            activeTab === "readme"
              ? "bg-graphite-900 text-white"
              : "border border-graphite-200 text-graphite-600 dark:border-graphite-700 dark:text-graphite-200"
          }`}
        >
          README
        </button>
        <button
          onClick={() => setActiveTab("onboarding")}
          className={`rounded-full px-3 py-1 text-xs font-semibold ${
            activeTab === "onboarding"
              ? "bg-graphite-900 text-white"
              : "border border-graphite-200 text-graphite-600 dark:border-graphite-700 dark:text-graphite-200"
          }`}
        >
          Onboarding
        </button>
      </div>
      <div className="mt-4 flex-1 overflow-y-auto rounded-2xl bg-white/80 p-4 text-xs text-graphite-700 shadow-sm dark:bg-graphite-900/70 dark:text-graphite-100">
        <ReactMarkdown remarkPlugins={[remarkGfm]}>{activeContent}</ReactMarkdown>
      </div>
    </section>
  );
});

MdViewer.displayName = "MdViewer";

export default MdViewer;
