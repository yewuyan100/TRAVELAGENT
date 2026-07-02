import type { SourceRef } from '../api/chat';

type Props = {
  source: SourceRef;
};

export default function SourceCard({ source }: Props) {
  return (
    <div className="source-card">
      <div className="source-title">{source.title}</div>
      <div className="source-meta">
        <span>{source.city}</span>
        <span>{source.category}</span>
        <span>{source.score.toFixed(2)}</span>
      </div>
    </div>
  );
}
