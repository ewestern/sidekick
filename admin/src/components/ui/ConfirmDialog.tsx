import { useCallback, useRef, useState } from "react";

type DialogOptions = {
  title: string;
  message: string;
  confirmLabel?: string;
  variant?: "danger" | "default";
};

type PendingConfirm = {
  opts: DialogOptions;
  resolve: (confirmed: boolean) => void;
};

export type UseConfirmReturn = {
  confirm: (opts: DialogOptions) => Promise<boolean>;
  dialog: React.ReactNode;
};

export function useConfirm(): UseConfirmReturn {
  const [pending, setPending] = useState<PendingConfirm | null>(null);
  const resolveRef = useRef<((v: boolean) => void) | null>(null);

  const confirm = useCallback((opts: DialogOptions): Promise<boolean> => {
    return new Promise((resolve) => {
      resolveRef.current = resolve;
      setPending({ opts, resolve });
    });
  }, []);

  const handle = (confirmed: boolean) => {
    resolveRef.current?.(confirmed);
    setPending(null);
  };

  const dialog = pending ? (
    <div className="dialog-overlay" onClick={() => handle(false)}>
      <div
        className="dialog"
        onClick={(e) => e.stopPropagation()}
        role="alertdialog"
      >
        <h3 className="dialog-title">{pending.opts.title}</h3>
        <p className="dialog-message">{pending.opts.message}</p>
        <div className="dialog-actions">
          <button onClick={() => handle(false)}>Cancel</button>
          <button
            className={pending.opts.variant === "danger" ? "danger" : "primary"}
            onClick={() => handle(true)}
          >
            {pending.opts.confirmLabel ?? "Confirm"}
          </button>
        </div>
      </div>
    </div>
  ) : null;

  return { confirm, dialog };
}
