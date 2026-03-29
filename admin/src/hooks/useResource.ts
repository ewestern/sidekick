import { useCallback, useEffect, useRef, useState } from "react";
import { useToast } from "./useToast";
import { parseApiError } from "../lib/api";

export type ExecOptions = {
  confirm?: string;
  successMsg?: string;
  skipRefresh?: boolean;
};

export type UseResourceReturn<T> = {
  rows: T[];
  selected: T | null;
  loading: boolean;
  listError: string | null;
  select: (item: T | null) => void;
  refresh: () => Promise<void>;
  exec: (
    action: () => Promise<unknown>,
    opts?: ExecOptions,
  ) => Promise<boolean>;
};

type ResourceConfig<T> = {
  list: () => Promise<unknown>;
  getId: (item: T) => string;
};

export function useResource<T>(
  config: ResourceConfig<T>,
): UseResourceReturn<T> {
  const { list, getId } = config;
  const toast = useToast();
  const [rows, setRows] = useState<T[]>([]);
  const [selected, setSelected] = useState<T | null>(null);
  const [loading, setLoading] = useState(false);
  const [listError, setListError] = useState<string | null>(null);
  const selectedIdRef = useRef<string | null>(null);

  const refresh = useCallback(async () => {
    try {
      const response = await list();
      const next = Array.isArray(response) ? (response as T[]) : [];
      setRows(next);
      // Re-select by ID after refresh so detail panel stays in sync
      if (selectedIdRef.current !== null) {
        const reselected =
          next.find((r) => getId(r) === selectedIdRef.current) ?? null;
        setSelected(reselected);
      }
    } catch (caught) {
      setListError(parseApiError(caught));
    }
  }, [list, getId]);

  useEffect(() => {
    void (async () => {
      setLoading(true);
      setListError(null);
      try {
        const response = await list();
        setRows(Array.isArray(response) ? (response as T[]) : []);
      } catch (caught) {
        setListError(parseApiError(caught));
      } finally {
        setLoading(false);
      }
    })();
  }, []); // eslint-disable-line react-hooks/exhaustive-deps

  const select = useCallback(
    (item: T | null) => {
      setSelected(item);
      selectedIdRef.current = item ? getId(item) : null;
    },
    [getId],
  );

  const exec = useCallback(
    async (
      action: () => Promise<unknown>,
      opts: ExecOptions = {},
    ): Promise<boolean> => {
      const { confirm, successMsg, skipRefresh } = opts;
      if (confirm && !window.confirm(confirm)) return false;
      setLoading(true);
      try {
        await action();
        if (!skipRefresh) await refresh();
        if (successMsg) toast.success(successMsg);
        return true;
      } catch (caught) {
        toast.error(parseApiError(caught));
        return false;
      } finally {
        setLoading(false);
      }
    },
    [refresh, toast],
  );

  return { rows, selected, loading, listError, select, refresh, exec };
}
