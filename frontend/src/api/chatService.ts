import { API_BASE_URL } from "@/api/client";
import { useChatStore } from "@/store/useChatStore";
import type { ChatMessage, DisplayType, ToolInvocation } from "@/types/chat";

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
    return { id: createId(), name: "weather", label: "天气工具", status: "running" };
  }
  if (/路线|行程|几天|怎么玩|三日游|两日游|顺序/.test(query)) {
    return { id: createId(), name: "map", label: "地图行程工具", status: "running" };
  }
  return { id: createId(), name: "rag", label: "本地 RAG 检索", status: "running" };
}

export async function sendStreamingChat(query: string): Promise<void> {
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
    createdAt: now + 1,
  };

  store.addMessage(userMessage);
  store.addMessage(assistantMessage);
  store.setStreaming(true);

  try {
    const response = await fetch(`${API_BASE_URL}/api/chat/stream`, {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
      },
      body: JSON.stringify({ query }),
    });

    if (!response.ok) {
      throw new Error(`请求失败：${response.status} ${response.statusText}`);
    }

    if (!response.body) {
      throw new Error("后端没有返回可读取的流。等待 /api/chat/stream 对齐后再试。 ");
    }

    const reader = response.body.getReader();
    const decoder = new TextDecoder("utf-8");

    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      const chunk = decoder.decode(value, { stream: true });

      // Reserved for future SSE / JSON Lines parsing.
      store.appendMessageContent(assistantId, chunk);
    }

    store.updateMessage(assistantId, {
      status: "completed",
      toolInvocations: [{ ...toolInvocation, status: "success" }],
    });
  } catch (error) {
    const message = error instanceof Error ? error.message : "网络错误，请稍后重试。";
    store.updateMessage(assistantId, {
      status: "failed",
      error: message,
      content: message,
      toolInvocations: [{ ...toolInvocation, status: "failed", message }],
    });
    throw error;
  } finally {
    useChatStore.getState().setStreaming(false);
  }
}
