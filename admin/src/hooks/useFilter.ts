import { useMemo, useState } from "react";

export type UseFilterReturn<T> = {
  query: string;
  setQuery: (q: string) => void;
  filtered: T[];
};

export function useFilter<T>(
  rows: T[],
  searchFields: (keyof T)[],
): UseFilterReturn<T> {
  const [query, setQuery] = useState("");

  const filtered = useMemo(() => {
    const q = query.trim().toLowerCase();
    if (!q) return rows;
    return rows.filter((row) =>
      searchFields.some((field) => {
        const val = row[field];
        return typeof val === "string" && val.toLowerCase().includes(q);
      }),
    );
  }, [rows, query, searchFields]);

  return { query, setQuery, filtered };
}
