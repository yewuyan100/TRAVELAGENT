import { apiClient, API_BASE_URL } from "@/api/client";
import type { RagSource } from "@/types/chat";

export { apiClient, API_BASE_URL };

export interface ChatApiResponse {
  answer: string;
  intent: string;
  selected_tool: string;
  confidence: number;
  sources: RagSource[];
  cards: unknown[];
  debug?: Record<string, unknown>;
}

export type ChatStreamEvent =
  | { type: "status"; stage?: string; message: string }
  | { type: "chunk"; content: string }
  | {
      type: "metadata";
      intent: string;
      selected_tool: string;
      confidence: number;
      sources: RagSource[];
      cards?: unknown[];
      debug?: Record<string, unknown>;
    }
  | { type: "error"; message: string }
  | { type: "done" };

function apiPath(path: string): string {
  const base = API_BASE_URL.replace(/\/$/, "");
  return base.endsWith("/api") ? path : `/api${path}`;
}

function apiUrl(path: string): string {
  const base = API_BASE_URL.replace(/\/$/, "");
  return `${base}${apiPath(path)}`;
}

export async function sendChat(question: string): Promise<ChatApiResponse> {
  const response = await apiClient.post<ChatApiResponse>(apiPath("/chat"), { question });
  return response.data;
}

export async function streamChat(
  question: string,
  onEvent: (event: ChatStreamEvent) => void
): Promise<void> {
  const response = await fetch(apiUrl("/chat/stream"), {
    method: "POST",
    headers: {
      "Content-Type": "application/json",
    },
    body: JSON.stringify({ question }),
  });

  if (!response.ok) {
    throw new Error(`流式请求失败：${response.status} ${response.statusText}`);
  }
  if (!response.body) {
    throw new Error("浏览器没有收到可读取的流式响应。");
  }

  const reader = response.body.getReader();
  const decoder = new TextDecoder("utf-8");
  let buffer = "";

  while (true) {
    const { done, value } = await reader.read();
    if (done) break;

    buffer += decoder.decode(value, { stream: true });
    const lines = buffer.split("\n");
    buffer = lines.pop() || "";

    for (const line of lines) {
      const trimmed = line.trim();
      if (!trimmed) continue;
      onEvent(JSON.parse(trimmed) as ChatStreamEvent);
    }
  }

  const tail = buffer.trim();
  if (tail) {
    onEvent(JSON.parse(tail) as ChatStreamEvent);
  }
}
