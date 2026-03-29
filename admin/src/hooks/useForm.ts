import { useCallback, useRef, useState } from "react";

export type UseFormReturn<T> = {
  values: T;
  set: <K extends keyof T>(field: K, value: T[K]) => void;
  setAll: (values: T) => void;
  reset: () => void;
  isDirty: boolean;
};

export function useForm<T>(defaults: T): UseFormReturn<T> {
  const defaultsRef = useRef(defaults);
  const [values, setValues] = useState<T>(defaults);
  const [isDirty, setIsDirty] = useState(false);

  const set = useCallback(<K extends keyof T>(field: K, value: T[K]) => {
    setValues((prev) => ({ ...prev, [field]: value }));
    setIsDirty(true);
  }, []);

  const setAll = useCallback((next: T) => {
    setValues(next);
    setIsDirty(false);
  }, []);

  const reset = useCallback(() => {
    setValues(defaultsRef.current);
    setIsDirty(false);
  }, []);

  return { values, set, setAll, reset, isDirty };
}
