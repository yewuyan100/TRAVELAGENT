import { AlertCircle, CheckCircle2, Cloud, Database, Loader2, Map, Search } from "lucide-react";
import type { ToolInvocation } from "@/types/chat";
import { cn } from "@/lib/utils";

interface ToolIndicatorProps {
  tools?: ToolInvocation[];
}

function iconFor(tool: ToolInvocation) {
  if (tool.status === "running") return <Loader2 className="h-3.5 w-3.5 animate-spin" />;
  if (tool.status === "failed") return <AlertCircle className="h-3.5 w-3.5" />;
  if (tool.status === "fallback") return <Search className="h-3.5 w-3.5" />;
  if (tool.name === "weather") return <Cloud className="h-3.5 w-3.5" />;
  if (tool.name === "map") return <Map className="h-3.5 w-3.5" />;
  if (tool.name === "rag") return <Database className="h-3.5 w-3.5" />;
  return tool.status === "success" ? <CheckCircle2 className="h-3.5 w-3.5" /> : <Search className="h-3.5 w-3.5" />;
}

export function ToolIndicator({ tools = [] }: ToolIndicatorProps) {
  if (!tools.length) return null;

  return (
    <div className="mt-3 flex flex-wrap gap-2">
      {tools.map((tool) => (
        <div
          key={tool.id}
          className={cn(
            "inline-flex items-center gap-1.5 rounded-full border px-2.5 py-1 text-xs",
            tool.status === "failed" && "border-red-200 bg-red-50 text-red-700",
            tool.status === "running" && "border-blue-200 bg-blue-50 text-blue-700",
            tool.status === "fallback" && "border-amber-200 bg-amber-50 text-amber-700",
            tool.status === "success" && "border-emerald-200 bg-emerald-50 text-emerald-700"
          )}
        >
          {iconFor(tool)}
          <span>{tool.label || tool.name}</span>
          {tool.message && <span className="text-slate-500">{tool.message}</span>}
        </div>
      ))}
    </div>
  );
}
