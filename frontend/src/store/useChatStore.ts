import { create } from "zustand";
import type { ChatMessage } from "@/types/chat";

interface ChatStore {
  messages: ChatMessage[];
  isStreaming: boolean;
  setStreaming: (value: boolean) => void;
  addMessage: (message: ChatMessage) => void;
  updateMessage: (id: string, patch: Partial<ChatMessage>) => void;
  appendMessageContent: (id: string, chunk: string) => void;
  setMessages: (messages: ChatMessage[]) => void;
  clearMessages: () => void;
  resetChat: () => void;
}

const createWelcomeMessage = (): ChatMessage => ({
  id: "welcome",
  role: "assistant",
  content: "你好，我是你的 AI 旅游助手。你可以问我城市攻略、天气、路线规划或旅行建议。",
  displayType: "text",
  status: "completed",
  createdAt: Date.now(),
});

export const useChatStore = create<ChatStore>((set) => ({
  messages: [createWelcomeMessage()],
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
        message.id === id
          ? { ...message, content: message.content + chunk }
          : message
      ),
    })),

  setMessages: (messages) => set({ messages }),

  clearMessages: () => set({ messages: [] }),

  resetChat: () => set({ messages: [createWelcomeMessage()] }),
}));
