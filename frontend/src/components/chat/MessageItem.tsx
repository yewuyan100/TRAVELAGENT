import ReactMarkdown from "react-markdown";
import { AlertCircle } from "lucide-react";
import { ToolIndicator } from "@/components/agent/ToolIndicator";
import { RagSection } from "@/components/agent/RagSection";
import { WeatherCard } from "@/components/cards/WeatherCard";
import { ItineraryCard } from "@/components/cards/ItineraryCard";
import { TravelRecommendationCard } from "@/components/cards/TravelRecommendationCard";
import type { ChatMessage } from "@/types/chat";
import { cn } from "@/lib/utils";

interface MessageItemProps {
  message: ChatMessage;
}

export function MessageItem({ message }: MessageItemProps) {
  const isUser = message.role === "user";
  const weatherData = message.metadata?.weatherData;
  const itinerary = message.metadata?.itinerary;
  const intent = message.metadata?.intent;
  const selectedTool = message.metadata?.selectedTool;
  const confidence = message.metadata?.confidence;
  const streamStatus = message.metadata?.streamStatus;

  return (
    <article className={cn("flex", isUser ? "justify-end" : "justify-start")}>
      <div
        className={cn(
          "max-w-[min(760px,100%)] rounded-2xl px-4 py-3 text-sm leading-7 shadow-sm",
          isUser
            ? "bg-slate-950 text-white"
            : "border border-slate-200 bg-white text-slate-800"
        )}
      >
        <div className={cn("markdown-body", isUser && "text-white")}>
          <ReactMarkdown>{message.content || (message.status === "streaming" ? "生成中..." : "")}</ReactMarkdown>
        </div>

        <ToolIndicator tools={message.toolInvocations} />
        {!isUser && (intent || selectedTool || typeof confidence === "number") && (
          <div className="mt-3 flex flex-wrap gap-2 text-xs text-slate-500">
            {intent && <span className="rounded-full bg-slate-100 px-2 py-1">意图：{String(intent)}</span>}
            {selectedTool && <span className="rounded-full bg-slate-100 px-2 py-1">工具：{String(selectedTool)}</span>}
            {typeof confidence === "number" && (
              <span className="rounded-full bg-slate-100 px-2 py-1">置信度：{confidence.toFixed(2)}</span>
            )}
          </div>
        )}
        <RagSection sources={message.ragSources} />
        <WeatherCard data={weatherData} />
        <ItineraryCard itinerary={itinerary} />
        {message.displayType === "travel" && !message.metadata?.itinerary && (
          <TravelRecommendationCard
            city="Travel Agent"
            title="旅行建议"
            description="后续可接入模型结构化输出，将城市推荐以卡片形式展示。"
            tags={["RAG", "Agent", "Travel"]}
          />
        )}

        {message.status === "streaming" && (
          <div className="mt-2 text-xs text-slate-500">{String(streamStatus || "生成中...")}</div>
        )}
        {message.status === "failed" && message.error && (
          <div className="mt-3 flex items-start gap-2 rounded-lg border border-red-200 bg-red-50 p-3 text-xs text-red-700">
            <AlertCircle className="mt-0.5 h-4 w-4 shrink-0" />
            <span>{message.error}</span>
          </div>
        )}
      </div>
    </article>
  );
}
