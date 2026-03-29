import { useContext } from "react";
import { ToastContext } from "../../hooks/useToast";

export function ToastContainer() {
  const ctx = useContext(ToastContext);
  if (!ctx || ctx.toasts.length === 0) return null;

  return (
    <div className="toast-container" role="status" aria-live="polite">
      {ctx.toasts.map((t) => (
        <div key={t.id} className={`toast toast-${t.variant}`}>
          <span>{t.message}</span>
          <button
            className="toast-dismiss"
            onClick={() => ctx.dismiss(t.id)}
            aria-label="Dismiss"
          >
            ×
          </button>
        </div>
      ))}
    </div>
  );
}
