import type { RagSource } from "@/types/chat";

interface SourceCardProps {
  source: RagSource;
}

export default function SourceCard({ source }: SourceCardProps) {
  return (
    <div className="rounded-lg border border-slate-200 bg-white p-3 text-sm">
      <div className="font-medium text-slate-900">{source.title}</div>
      <div className="mt-1 text-xs text-slate-500">{source.source || "local"} {typeof source.score === "number" ? `· ${source.score.toFixed(2)}` : ""}</div>
    </div>
  );
}
