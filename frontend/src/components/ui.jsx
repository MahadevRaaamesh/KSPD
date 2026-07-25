import { Database, TriangleAlert } from 'lucide-react';

/** Panel section header with micro-label + optional right-side content. */
export function PanelHeader({ label, title, right }) {
  return (
    <div className="panel-header">
      <div>
        {label && <div className="micro-label" style={{ marginBottom: 3 }}><span className="tick" />{label}</div>}
        {title && <div className="panel-title">{title}</div>}
      </div>
      {right}
    </div>
  );
}

export function EmptyState({ icon: Icon = Database, title = 'No data', sub }) {
  return (
    <div className="empty-state">
      <Icon size={30} />
      <div className="empty-title">{title}</div>
      {sub && <div className="empty-sub">{sub}</div>}
    </div>
  );
}

export function ErrorState({ message, onRetry }) {
  return (
    <div className="empty-state">
      <TriangleAlert size={30} color="var(--status-serious)" />
      <div className="empty-title">Could not load data</div>
      <div className="empty-sub">{message}</div>
      {onRetry && <button className="btn" onClick={onRetry}>Retry</button>}
    </div>
  );
}

export function Skeleton({ h = 200, style }) {
  return <div className="skeleton" style={{ height: h, width: '100%', ...style }} />;
}
