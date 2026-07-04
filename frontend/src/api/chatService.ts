import { sendChat, streamChat, type ChatApiResponse, type ChatStreamEvent } from "@/api/chat";
import { useChatStore } from "@/store/useChatStore";
import type { ChatMessage, DisplayType, ItineraryDay, ToolInvocation, ToolUsage, WeatherData } from "@/types/chat";

const createId = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

function inferDisplayType(query: string): DisplayType {
  if (/天气|下雨|气温|温度/.test(query)) return "weather";
  if (/路线|行程|几天|怎么玩|三日游|两日游|自由行|规划|顺序/.test(query)) return "itinerary";
  if (/推荐|景点|美食|旅行|吃|火锅|小吃/.test(query)) return "travel";
  return "text";
}

function inferToolInvocation(query: string): ToolInvocation {
  if (/天气|下雨|气温|温度|明天|后天/.test(query)) {
    return { id: createId(), name: "weather", label: "天气工具", status: "running", message: "准备查询" };
  }
  if (/路线|行程|几天|怎么玩|三日游|两日游|自由行|规划|顺序|怎么走/.test(query)) {
    return { id: createId(), name: "map", label: "地图/行程", status: "running", message: "准备规划" };
  }
  return { id: createId(), name: "rag", label: "知识库", status: "running", message: "准备检索" };
}

function normalizeToolName(tool: string): ToolInvocation["name"] {
  if (tool.includes("weather")) return "weather";
  if (tool.includes("map") || tool.includes("itinerary")) return "map";
  if (tool.includes("rag")) return "rag";
  return tool || "agent";
}

function toolLabel(tool: string): string {
  if (tool.includes("weather")) return "天气工具";
  if (tool.includes("map") || tool.includes("itinerary")) return "地图/行程";
  if (tool.includes("rag")) return "知识库";
  if (tool === "agent") return "Agent";
  if (tool === "multi_tool") return "综合决策";
  if (tool === "refuse") return "能力边界";
  return tool || "Agent";
}

function toolInvocationsFromTrace(tools: ToolUsage[] | undefined, fallback: ToolInvocation): ToolInvocation[] {
  if (!tools?.length) return [{ ...fallback, status: "success", message: "完成" }];
  return tools.map((tool) => ({
    id: `${tool.tool}-${createId()}`,
    name: normalizeToolName(tool.tool),
    label: toolLabel(tool.tool),
    status: tool.status === "failed" ? "failed" : tool.status === "fallback" ? "fallback" : "success",
    message: tool.summary,
  }));
}

function cardData<T>(cards: unknown[] | undefined, type: string): T | undefined {
  const card = (cards || []).find((item) => {
    if (!item || typeof item !== "object") return false;
    return (item as { type?: string }).type === type;
  }) as { data?: T } | undefined;
  return card?.data;
}

function weatherFromCards(cards: unknown[] | undefined): WeatherData | undefined {
  return cardData<WeatherData>(cards, "weather");
}

function normalizeRoutes(routes: unknown): ItineraryDay["routes"] {
  if (!Array.isArray(routes)) return [];
  return routes
    .filter((route) => route && typeof route === "object")
    .map((route) => {
      const item = route as {
        from?: string;
        to?: string;
        path?: Array<[number, number]>;
        distance_m?: number;
        duration_min?: number;
        mode?: string;
      };
      return {
        from: item.from,
        to: item.to,
        path: Array.isArray(item.path) ? item.path : undefined,
        distance_m: item.distance_m,
        duration_min: item.duration_min,
        mode: item.mode,
      };
    });
}

function normalizeApiItinerary(itinerary: ChatApiResponse["itinerary"]): ItineraryDay[] | undefined {
  if (!itinerary?.length) return undefined;
  return itinerary.map((day) => ({
    day: `Day ${day.day}`,
    title: day.theme,
    theme: day.theme,
    pace: day.pace,
    stops: (day.spots || []).map((spot) => ({
      title: spot.name,
      name: spot.name,
      type: spot.type,
      description: spot.description,
      lat: spot.lat,
      lng: spot.lng,
      latitude: spot.lat,
      longitude: spot.lng,
    })),
    routes: day.routes || [],
    notes: day.notes,
  }));
}

function itineraryFromCards(cards: unknown[] | undefined): ItineraryDay[] | undefined {
  const data = cardData<Record<string, unknown>>(cards, "itinerary");
  if (!data) return undefined;

  const days = Array.isArray(data.days) ? data.days : Array.isArray(data.itinerary) ? data.itinerary : [];
  return days.map((day, index) => {
    const item = day as {
      day?: number | string;
      theme?: string;
      title?: string;
      pace?: string;
      spots?: Array<{ name?: string; title?: string; type?: string; lat?: number; lng?: number }>;
      places?: string[];
      routes?: unknown;
      notes?: string;
      note?: string;
    };
    const stops =
      item.spots?.map((spot) => ({
        title: spot.name || spot.title || "未命名地点",
        name: spot.name || spot.title,
        type: spot.type,
        lat: spot.lat,
        lng: spot.lng,
        latitude: spot.lat,
        longitude: spot.lng,
      })) || (item.places || []).map((place) => ({ title: place, name: place }));

    return {
      day: `Day ${item.day || index + 1}`,
      title: item.theme || item.title,
      pace: item.pace,
      stops,
      routes: normalizeRoutes(item.routes),
      notes: item.notes || item.note,
    };
  });
}

function itineraryFromResponse(data: { itinerary?: ChatApiResponse["itinerary"]; cards?: unknown[] }) {
  return normalizeApiItinerary(data.itinerary) || itineraryFromCards(data.cards);
}

function completeMessage(
  assistantId: string,
  query: string,
  toolInvocation: ToolInvocation,
  data: ChatApiResponse | Extract<ChatStreamEvent, { type: "metadata" }>,
  content?: string
) {
  const selectedTool = data.selected_tool || toolInvocation.name;
  const store = useChatStore.getState();
  const existingContent = store.messages.find((message) => message.id === assistantId)?.content || "";
  store.updateMessage(assistantId, {
    content: content ?? existingContent,
    status: "completed",
    displayType: inferDisplayType(`${query} ${data.intent}`),
    toolInvocations: toolInvocationsFromTrace(data.tools_used, toolInvocation),
    ragSources: data.sources || [],
    metadata: {
      intent: data.intent,
      selectedTool,
      confidence: data.confidence,
      cards: data.cards || [],
      city: data.city,
      weatherData: weatherFromCards(data.cards),
      itinerary: itineraryFromResponse(data),
      foodRecommendations: data.food_recommendations || [],
      tips: data.tips || [],
      taskPlan: data.task_plan || [],
      toolsUsed: data.tools_used || [],
      retrievedChunks: data.retrieved_chunks || [],
      traceMetadata: data.metadata || {},
    },
  });
  useChatStore.getState().saveCurrentConversation();
}

async function fallbackToNonStreaming(
  query: string,
  assistantId: string,
  toolInvocation: ToolInvocation,
  reason: string
) {
  const store = useChatStore.getState();
  store.updateMessage(assistantId, {
    content: "",
    status: "streaming",
    toolInvocations: [{ ...toolInvocation, status: "running", message: "切换普通接口" }],
    metadata: { streamStatus: reason },
  });
  const data = await sendChat(query);
  completeMessage(assistantId, query, toolInvocation, data, data.answer);
}

export async function sendChatMessage(query: string): Promise<void> {
  const store = useChatStore.getState();
  const now = Date.now();
  const userMessage: ChatMessage = {
    id: createId(),
    role: "user",
    content: query,
    status: "completed",
    displayType: "text",
    createdAt: now,
  };
  const toolInvocation = inferToolInvocation(query);
  const assistantId = createId();
  const assistantMessage: ChatMessage = {
    id: assistantId,
    role: "assistant",
    content: "",
    status: "streaming",
    displayType: inferDisplayType(query),
    toolInvocations: [toolInvocation],
    metadata: { streamStatus: "正在连接旅行助手" },
    createdAt: now + 1,
  };

  store.addMessage(userMessage);
  store.addMessage(assistantMessage);
  store.setStreaming(true);

  try {
    let receivedMetadata = false;
    await streamChat(query, (event) => {
      const current = useChatStore.getState();
      if (event.type === "status") {
        current.updateMessage(assistantId, {
          toolInvocations: [{ ...toolInvocation, status: "running", message: event.message }],
          metadata: { streamStatus: event.message },
        });
        return;
      }
      if (event.type === "chunk") {
        current.appendMessageContent(assistantId, event.content);
        return;
      }
      if (event.type === "metadata") {
        receivedMetadata = true;
        completeMessage(assistantId, query, toolInvocation, event);
        return;
      }
      if (event.type === "error") {
        throw new Error(event.message);
      }
      if (event.type === "done") {
        current.updateMessage(assistantId, { status: "completed" });
      }
    });

    if (!receivedMetadata) {
      useChatStore.getState().updateMessage(assistantId, { status: "completed" });
      useChatStore.getState().saveCurrentConversation();
    }
  } catch (error) {
    const reason = error instanceof Error ? error.message : "流式接口不可用";
    try {
      await fallbackToNonStreaming(query, assistantId, toolInvocation, reason);
    } catch (fallbackError) {
      const message = fallbackError instanceof Error ? fallbackError.message : "网络错误，请稍后重试。";
      store.updateMessage(assistantId, {
        status: "failed",
        error: message,
        content: `抱歉，这次请求没有成功：${message}`,
        toolInvocations: [{ ...toolInvocation, status: "failed", message }],
      });
      useChatStore.getState().saveCurrentConversation();
      throw fallbackError;
    }
  } finally {
    useChatStore.getState().setStreaming(false);
  }
}

export const sendStreamingChat = sendChatMessage;
