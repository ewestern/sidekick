type StatusBadgeProps = {
  value: string | null | undefined;
};

export function StatusBadge({ value }: StatusBadgeProps) {
  if (!value) return <span className="status-badge">—</span>;
  return <span className={`status-badge status-${value}`}>{value}</span>;
}
