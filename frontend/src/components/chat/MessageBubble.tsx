import ReactMarkdown from "react-markdown";
import { AlertCircle, Bot, CheckCircle2, Loader2, UserRound } from "lucide-react";
import { AgentTracePanel } from "@/components/agent/AgentTracePanel";
import { ToolIndicator } from "@/components/agent/ToolIndicator";
import { ItineraryCard } from "@/components/cards/ItineraryCard";
import { WeatherCard } from "@/components/cards/WeatherCard";
import type { ChatMessage } from "@/types/chat";
import { cn } from "@/lib/utils";

interface MessageBubbleProps {
  message: ChatMessage;
  compact?: boolean;
}

export function MessageBubble({ message, compact = false }: MessageBubbleProps) {
  const isUser = message.role === "user";
  const itinerary =
    message.metadata?.intent === "itinerary_plan" || message.metadata?.intent === "map_query"
      ? message.metadata?.itinerary
      : undefined;
  const weatherData = message.metadata?.weatherData;
  const isLoading = message.status === "streaming";

  return (
    <article className={cn("flex gap-3", isUser ? "justify-end" : "justify-start")}>
      {!isUser && !compact && (
        <span className="mt-1 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full border border-emerald-200 bg-emerald-50 text-emerald-700">
          <Bot className="h-5 w-5" />
        </span>
      )}

      <div className={cn(compact ? "max-w-[min(760px,100%)]" : "max-w-[min(820px,calc(100%-52px))]", isUser && "flex flex-col items-end")}>
        <div
          className={cn(
            "rounded-lg px-4 py-3 text-sm leading-7 shadow-sm",
            isUser ? "bg-emerald-100 text-slate-900" : "border border-slate-200 bg-white text-slate-800"
          )}
        >
          {isLoading && !message.content ? (
            <div className="flex items-center gap-2 text-slate-500">
              <Loader2 className="h-4 w-4 animate-spin" />
              {String(message.metadata?.streamStatus || "正在生成旅行建议...")}
            </div>
          ) : (
            <div className="markdown-body">
              <ReactMarkdown>{message.content || ""}</ReactMarkdown>
            </div>
          )}

          {message.status === "failed" && message.error && (
            <div className="mt-3 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">
              <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
              <span>{message.error}</span>
            </div>
          )}
        </div>

        {!isUser && (
          <>
            <ToolIndicator tools={message.toolInvocations} />
            {!compact && (
              <>
                <WeatherCard data={weatherData} />
                <ItineraryCard itinerary={itinerary} city={message.metadata?.city} />
              </>
            )}
            <AgentTracePanel metadata={message.metadata} />
            <div className="mt-2 flex flex-wrap items-center gap-2 text-xs text-slate-400">
              {isLoading ? (
                <span className="inline-flex items-center gap-1">
                  <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  {String(message.metadata?.streamStatus || "处理中")}
                </span>
              ) : (
                <span className="inline-flex items-center gap-1">
                  <CheckCircle2 className="h-3.5 w-3.5 text-emerald-500" />
                  已完成
                </span>
              )}
              {message.metadata?.intent && <span>Intent: {String(message.metadata.intent)}</span>}
              {message.metadata?.retrievedChunks?.length ? <span>知识片段：{message.metadata.retrievedChunks.length} 条</span> : null}
            </div>
          </>
        )}
      </div>

      {isUser && !compact && (
        <span className="mt-1 inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-full bg-slate-900 text-white">
          <UserRound className="h-5 w-5" />
        </span>
      )}
    </article>
  );
}
