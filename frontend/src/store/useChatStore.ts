import { create } from "zustand";
import type { ChatMessage, ConversationHistory } from "@/types/chat";

const HISTORY_KEY = "travel-agent-conversations";
const MAX_HISTORY = 8;

const createId = () =>
  typeof crypto !== "undefined" && "randomUUID" in crypto
    ? crypto.randomUUID()
    : `${Date.now()}-${Math.random().toString(16).slice(2)}`;

function readHistories(): ConversationHistory[] {
  if (typeof window === "undefined") return [];
  try {
    const raw = window.localStorage.getItem(HISTORY_KEY);
    return raw ? (JSON.parse(raw) as ConversationHistory[]) : [];
  } catch {
    return [];
  }
}

function writeHistories(histories: ConversationHistory[]) {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(HISTORY_KEY, JSON.stringify(histories.slice(0, MAX_HISTORY)));
}

function meaningfulMessages(messages: ChatMessage[]) {
  return messages.filter((message) => message.id !== "welcome" && message.content.trim());
}

function titleFromMessages(messages: ChatMessage[]) {
  const firstUser = messages.find((message) => message.role === "user" && message.content.trim());
  return firstUser?.content.trim().slice(0, 18) || "新的旅行对话";
}

interface ChatStore {
  messages: ChatMessage[];
  activeSessionId: string;
  histories: ConversationHistory[];
  isStreaming: boolean;
  setStreaming: (value: boolean) => void;
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, patch: Partial<ChatMessage>) => void;
  appendMessageContent: (id: string, chunk: string) => void;
  setMessages: (messages: ChatMessage[]) => void;
  clearMessages: () => void;
  saveCurrentConversation: () => void;
  beginNewSession: () => void;
  restoreConversation: (id: string) => void;
  resetChat: () => void;
}

const createWelcomeMessage = (): ChatMessage => ({
  id: "welcome",
  role: "assistant",
  content: "您好，旅行者。我可以帮你规划行程、推荐景点、查询天气，也能解释每一步调用了哪些工具。",
  displayType: "text",
  status: "completed",
  createdAt: Date.now(),
});

export const useChatStore = create<ChatStore>((set, get) => ({
  messages: [createWelcomeMessage()],
  activeSessionId: createId(),
  histories: readHistories(),
  isStreaming: false,

  setStreaming: (value) => set({ isStreaming: value }),

  addMessage: (message) =>
    set((state) => ({
      messages: [...state.messages, message],
    })),

  updateMessage: (id, patch) =>
    set((state) => ({
      messages: state.messages.map((message) =>
        message.id === id ? { ...message, ...patch } : message
      ),
    })),

  appendMessageContent: (id, chunk) =>
    set((state) => ({
      messages: state.messages.map((message) =>
        message.id === id ? { ...message, content: message.content + chunk } : message
      ),
    })),

  setMessages: (messages) => set({ messages }),

  clearMessages: () => set({ messages: [] }),

  saveCurrentConversation: () => {
    const state = get();
    if (meaningfulMessages(state.messages).length === 0) return;

    const entry: ConversationHistory = {
      id: state.activeSessionId,
      title: titleFromMessages(state.messages),
      messages: state.messages,
      updatedAt: Date.now(),
    };
    const histories = [entry, ...state.histories.filter((item) => item.id !== entry.id)].slice(0, MAX_HISTORY);
    writeHistories(histories);
    set({ histories });
  },

  beginNewSession: () => {
    get().saveCurrentConversation();
    set({
      activeSessionId: createId(),
      messages: [createWelcomeMessage()],
      isStreaming: false,
    });
  },

  restoreConversation: (id) => {
    get().saveCurrentConversation();
    const target = get().histories.find((item) => item.id === id);
    if (!target) return;
    set({
      activeSessionId: target.id,
      messages: target.messages,
      isStreaming: false,
    });
  },

  resetChat: () => get().beginNewSession(),
}));
