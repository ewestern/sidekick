type EmptyStateProps = {
  message: string;
  description?: string;
};

export function EmptyState({ message, description }: EmptyStateProps) {
  return (
    <div className="empty-state">
      <p className="empty-state-message">{message}</p>
      {description && <p className="empty-state-description">{description}</p>}
    </div>
  );
}
