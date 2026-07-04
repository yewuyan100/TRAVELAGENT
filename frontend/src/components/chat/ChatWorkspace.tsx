import { useEffect, useMemo, useRef } from "react";
import { CalendarDays, CircleDot, Loader2, MapPin, Sparkles } from "lucide-react";
import { ChatInput } from "@/components/chat/ChatInput";
import { MessageBubble } from "@/components/chat/MessageBubble";
import { useChatStore } from "@/store/useChatStore";
import type { ChatMessage, ItineraryDay } from "@/types/chat";

function latestPlan(messages: ChatMessage[]) {
  return [...messages]
    .reverse()
    .find((message) => message.role === "assistant" && message.metadata?.itinerary?.length);
}

function dayTitle(day: ItineraryDay, index: number) {
  return day.title || day.theme || `Day ${index + 1}`;
}

export function ChatWorkspace() {
  const messages = useChatStore((state) => state.messages);
  const isStreaming = useChatStore((state) => state.isStreaming);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  const visibleMessages = messages.filter((message) => message.id !== "welcome");
  const planMessage = useMemo(() => latestPlan(messages), [messages]);
  const itinerary = planMessage?.metadata?.itinerary || [];
  const city = planMessage?.metadata?.city;

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  return (
    <section className="flex min-h-0 flex-1 flex-col bg-white">
      <div className="min-h-0 flex-1 overflow-y-auto px-4 py-6 md:px-8">
        <div className="mx-auto flex max-w-6xl flex-col gap-5">
          <div className="flex flex-wrap items-start justify-between gap-4 rounded-lg border border-emerald-100 bg-emerald-50/50 px-5 py-4">
            <div>
              <div className="flex items-center gap-2 text-sm font-semibold text-emerald-800">
                <Sparkles className="h-4 w-4" />
                旅行助手工作台
              </div>
              <h2 className="mt-2 text-2xl font-semibold tracking-normal text-slate-950">
                {city ? `${city}旅行计划` : "从一个旅行问题开始"}
              </h2>
              <p className="mt-1 text-sm leading-6 text-slate-500">
                {city ? "你可以继续补充偏好，我会把新的工具调用和知识召回过程展示出来。" : "输入目的地、天气、路线或偏好后，这里会展示回答和 Agent 执行过程。"}
              </p>
            </div>
            {isStreaming && (
              <div className="inline-flex items-center gap-2 rounded-full bg-white px-3 py-2 text-xs text-emerald-700 shadow-sm">
                <Loader2 className="h-3.5 w-3.5 animate-spin" />
                正在整理
              </div>
            )}
          </div>

          {itinerary.length > 0 ? (
            <div className="grid gap-4 lg:grid-cols-3">
              {itinerary.map((day, index) => (
                <section key={day.day} className="flex min-h-[360px] flex-col rounded-lg border border-slate-200 bg-slate-50/70">
                  <div className="border-b border-slate-200 bg-white px-4 py-4">
                    <div className="flex items-center justify-between gap-3">
                      <div>
                        <div className="text-xs font-semibold uppercase tracking-wide text-emerald-700">Day {index + 1}</div>
                        <h3 className="mt-1 text-base font-semibold text-slate-950">{dayTitle(day, index)}</h3>
                      </div>
                      {day.pace && <span className="rounded-full bg-emerald-50 px-2.5 py-1 text-xs text-emerald-700">{day.pace}</span>}
                    </div>
                  </div>

                  <div className="flex flex-1 flex-col gap-3 p-3">
                    {day.stops.length === 0 ? (
                      <div className="rounded-lg border border-dashed border-slate-200 bg-white p-4 text-sm text-slate-500">
                        这一日还没有具体安排。
                      </div>
                    ) : (
                      day.stops.map((stop, stopIndex) => (
                        <div key={`${stop.title}-${stopIndex}`} className="rounded-lg border border-slate-200 bg-white p-3 text-left shadow-sm">
                          <div className="flex items-start gap-2">
                            <CircleDot className="mt-0.5 h-4 w-4 shrink-0 text-emerald-600" />
                            <div className="min-w-0">
                              <div className="truncate text-sm font-semibold text-slate-900">{stop.title}</div>
                              {stop.type && <div className="mt-1 text-xs text-slate-500">{stop.type}</div>}
                              {stop.location && (
                                <div className="mt-2 flex items-center gap-1 text-xs text-slate-500">
                                  <MapPin className="h-3.5 w-3.5" />
                                  {stop.location}
                                </div>
                              )}
                            </div>
                          </div>
                        </div>
                      ))
                    )}
                  </div>

                  {day.notes && <p className="border-t border-slate-200 bg-white px-4 py-3 text-xs leading-5 text-slate-500">{day.notes}</p>}
                </section>
              ))}
            </div>
          ) : (
            <div className="grid min-h-[360px] place-items-center rounded-lg border border-dashed border-slate-200 bg-slate-50/70 p-8 text-center">
              <div className="max-w-md">
                <span className="mx-auto inline-flex h-12 w-12 items-center justify-center rounded-lg bg-white text-emerald-700 shadow-sm">
                  <CalendarDays className="h-6 w-6" />
                </span>
                <h3 className="mt-4 text-lg font-semibold text-slate-950">还没有行程看板</h3>
                <p className="mt-2 text-sm leading-6 text-slate-500">
                  例如输入“为我规划 3 天成都自由行，喜欢美食和慢节奏”，生成后会在这里按天展示。
                </p>
              </div>
            </div>
          )}

          {visibleMessages.length > 0 && (
            <section className="rounded-lg border border-slate-200 bg-white p-4">
              <div className="mb-4 text-sm font-semibold text-slate-900">对话记录</div>
              <div className="flex flex-col gap-4">
                {visibleMessages.map((message) => (
                  <MessageBubble key={message.id} message={message} compact />
                ))}
                <div ref={bottomRef} />
              </div>
            </section>
          )}
        </div>
      </div>

      <ChatInput />
    </section>
  );
}
