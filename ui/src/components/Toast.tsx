import { memo } from "react";

export interface ToastItem {
  id: string;
  message: string;
  tone?: "error" | "info" | "success";
}

interface ToastProps {
  toasts: ToastItem[];
  onDismiss: (id: string) => void;
}

const Toast = memo(({ toasts, onDismiss }: ToastProps) => {
  return (
    <div className="fixed right-6 top-6 z-[90] flex max-w-sm flex-col gap-3 md:bottom-auto md:right-6 md:top-6 max-md:bottom-4 max-md:left-4 max-md:right-4 max-md:top-auto">
      {toasts.map((toast) => (
        <div
          key={toast.id}
          className={`rounded-2xl border px-4 py-3 text-xs shadow-soft backdrop-blur ${
            toast.tone === "error"
              ? "border-rose-500/40 bg-rose-500/20 text-rose-100"
              : toast.tone === "success"
              ? "border-signal-500/40 bg-signal-500/20 text-graphite-900"
              : "border-graphite-200 bg-white/80 text-graphite-700 dark:border-graphite-700 dark:bg-graphite-900/80 dark:text-graphite-100"
          }`}
        >
          <div className="flex items-start justify-between gap-3">
            <p className="leading-relaxed">{toast.message}</p>
            <button
              onClick={() => onDismiss(toast.id)}
              className="rounded-full border border-transparent px-2 py-1 text-[10px] uppercase tracking-[0.2em] text-graphite-200/80 hover:border-graphite-400"
            >
              Close
            </button>
          </div>
        </div>
      ))}
    </div>
  );
});

Toast.displayName = "Toast";

export default Toast;
