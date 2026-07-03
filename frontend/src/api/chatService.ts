import { sendChat, streamChat, type ChatApiResponse, type ChatStreamEvent } from "@/api/chat";
import { useChatStore } from "@/store/useChatStore";
import type { ChatMessage, DisplayType, ItineraryDay, ToolInvocation, WeatherData } from "@/types/chat";

const createId = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

function inferDisplayType(query: string): DisplayType {
  if (/天气|下雨|气温|温度/.test(query)) return "weather";
  if (/路线|行程|几天|怎么玩|三日游|两日游|顺序/.test(query)) return "itinerary";
  if (/推荐|景点|美食|旅游|旅行/.test(query)) return "travel";
  return "text";
}

function inferToolInvocation(query: string): ToolInvocation {
  if (/天气|下雨|气温|温度/.test(query)) {
    return { id: createId(), name: "weather", label: "天气工具", status: "running", message: "准备调用" };
  }
  if (/路线|行程|几天|怎么玩|三日游|两日游|顺序/.test(query)) {
    return { id: createId(), name: "map", label: "地图行程工具", status: "running", message: "准备调用" };
  }
  return { id: createId(), name: "rag", label: "本地 RAG", status: "running", message: "准备检索" };
}

function normalizeToolName(selectedTool: string): ToolInvocation["name"] {
  if (selectedTool.includes("weather")) return "weather";
  if (selectedTool.includes("map")) return "map";
  if (selectedTool.includes("rag")) return "rag";
  return selectedTool;
}

function toolLabel(selectedTool: string): string {
  if (selectedTool.includes("weather")) return "天气工具";
  if (selectedTool.includes("map")) return "地图行程工具";
  if (selectedTool.includes("rag")) return "本地 RAG";
  if (selectedTool === "refuse") return "拒答保护";
  return selectedTool || "Agent";
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

function asNumber(value: unknown): number | undefined {
  if (typeof value === "number" && Number.isFinite(value)) return value;
  if (typeof value === "string" && value.trim()) {
    const parsed = Number(value);
    return Number.isFinite(parsed) ? parsed : undefined;
  }
  return undefined;
}

function normalizeSpot(spot: unknown): ItineraryDay["stops"][number] {
  if (typeof spot === "string") {
    return { title: spot };
  }
  if (!spot || typeof spot !== "object") {
    return { title: "未命名景点" };
  }
  const item = spot as {
    name?: string;
    title?: string;
    address?: string;
    location?: string;
    type?: string;
    lat?: unknown;
    lng?: unknown;
    latitude?: unknown;
    longitude?: unknown;
  };
  const lat = asNumber(item.lat ?? item.latitude);
  const lng = asNumber(item.lng ?? item.longitude);
  return {
    title: item.name || item.title || "未命名景点",
    address: item.address,
    location: item.location,
    type: item.type,
    lat,
    lng,
    latitude: lat,
    longitude: lng,
    description: item.type ? `类型：${item.type}` : undefined,
  };
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

function itineraryFromCards(cards: unknown[] | undefined): ItineraryDay[] | undefined {
  const data = cardData<Record<string, unknown>>(cards, "itinerary") || cardData<Record<string, unknown>>(cards, "map_itinerary");
  if (!data) return undefined;

  const structuredDays = Array.isArray(data.days) ? data.days : undefined;
  if (structuredDays) {
    return structuredDays.map((day) => {
      const item = day as {
        day?: number | string;
        theme?: string;
        title?: string;
        pace?: string;
        spots?: unknown[];
        places?: unknown[];
        routes?: unknown;
        notes?: string;
        note?: string;
      };
      return {
        day: `Day ${item.day || ""}`.trim(),
        title: item.theme || item.title,
        pace: item.pace,
        stops: (item.spots || item.places || []).map(normalizeSpot),
        routes: normalizeRoutes(item.routes),
        notes: item.notes || item.note,
      };
    });
  }

  if (Array.isArray(data.spots)) {
    return [
      {
        day: "Day 1",
        title: typeof data.theme === "string" ? data.theme : "路线地图",
        stops: data.spots.map(normalizeSpot),
        routes: normalizeRoutes(data.routes),
        notes: typeof data.message === "string" ? data.message : undefined,
      },
    ];
  }

  const legacy = Array.isArray(data.itinerary) ? data.itinerary : [];
  return legacy.map((day) => {
    const item = day as { day?: number | string; theme?: string; places?: string[]; note?: string };
    return {
      day: `Day ${item.day || ""}`.trim(),
      title: item.theme,
      stops: (item.places || []).map(normalizeSpot),
      notes: item.note,
    };
  });
}

function applyChatResponse(
  assistantId: string,
  query: string,
  toolInvocation: ToolInvocation,
  data: ChatApiResponse
) {
  const selectedTool = data.selected_tool || toolInvocation.name;
  useChatStore.getState().updateMessage(assistantId, {
    content: data.answer,
    status: "completed",
    displayType: inferDisplayType(`${query} ${data.intent}`),
    toolInvocations: [
      {
        ...toolInvocation,
        name: normalizeToolName(selectedTool),
        label: toolLabel(selectedTool),
        status: "success",
        message: "完成",
      },
    ],
    ragSources: data.sources || [],
      metadata: {
        intent: data.intent,
        selectedTool,
        confidence: data.confidence,
        cards: data.cards || [],
        weatherData: weatherFromCards(data.cards),
        itinerary: itineraryFromCards(data.cards),
        streamStatus: "已使用非流式接口",
      },
  });
}

function applyStreamMetadata(
  assistantId: string,
  query: string,
  toolInvocation: ToolInvocation,
  event: Extract<ChatStreamEvent, { type: "metadata" }>
) {
  const selectedTool = event.selected_tool || toolInvocation.name;
  useChatStore.getState().updateMessage(assistantId, {
    displayType: inferDisplayType(`${query} ${event.intent}`),
    toolInvocations: [
      {
        ...toolInvocation,
        name: normalizeToolName(selectedTool),
        label: toolLabel(selectedTool),
        status: "success",
        message: "完成",
      },
    ],
    ragSources: event.sources || [],
    metadata: {
      intent: event.intent,
      selectedTool,
      confidence: event.confidence,
      cards: event.cards || [],
      weatherData: weatherFromCards(event.cards),
      itinerary: itineraryFromCards(event.cards),
      streamStatus: "已使用伪流式接口",
    },
  });
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
    toolInvocations: [{ ...toolInvocation, status: "running", message: "流式失败，切换普通接口" }],
    metadata: { streamStatus: reason },
  });
  const data = await sendChat(query);
  applyChatResponse(assistantId, query, toolInvocation, data);
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
    metadata: { streamStatus: "正在连接流式接口" },
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
        applyStreamMetadata(assistantId, query, toolInvocation, event);
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
        content: message,
        toolInvocations: [{ ...toolInvocation, status: "failed", message }],
      });
      throw fallbackError;
    }
  } finally {
    useChatStore.getState().setStreaming(false);
  }
}

export const sendStreamingChat = sendChatMessage;
