import { useState } from "react";
import { SendHorizontal } from "lucide-react";
import { sendChatMessage } from "@/api/chatService";
import { useChatStore } from "@/store/useChatStore";

export function ChatInput() {
  const [value, setValue] = useState("");
  const [notice, setNotice] = useState("Enter 发送，Shift + Enter 换行");
  const isStreaming = useChatStore((state) => state.isStreaming);

  async function submit() {
    const query = value.trim();
    if (!query || isStreaming) return;
    setValue("");
    setNotice("正在分析问题并调用工具...");

    try {
      await sendChatMessage(query);
      setNotice("已更新回答。你可以继续补充偏好或调整问题。");
    } catch {
      setNotice("请求失败，请检查后端服务或稍后重试。");
    }
  }

  return (
    <footer className="shrink-0 border-t border-slate-100 bg-white px-4 pb-5 pt-3">
      <div className="flex items-end gap-3 rounded-lg border border-emerald-200 bg-white p-3 shadow-sm focus-within:border-emerald-400">
        <textarea
          value={value}
          disabled={isStreaming}
          rows={2}
          placeholder={isStreaming ? "旅行助手正在整理..." : "输入你的旅行问题..."}
          className="max-h-36 min-h-12 flex-1 resize-none border-0 bg-transparent px-1 text-sm leading-6 text-slate-800 outline-none placeholder:text-slate-400 disabled:cursor-not-allowed"
          onChange={(event) => setValue(event.target.value)}
          onKeyDown={(event) => {
            if (event.key === "Enter" && !event.shiftKey) {
              event.preventDefault();
              void submit();
            }
          }}
        />

        <button
          type="button"
          disabled={!value.trim() || isStreaming}
          onClick={() => void submit()}
          className="inline-flex h-11 w-11 shrink-0 items-center justify-center rounded-full bg-emerald-700 text-white transition hover:bg-emerald-800 disabled:cursor-not-allowed disabled:bg-slate-300"
          aria-label="发送"
        >
          <SendHorizontal className="h-5 w-5" />
        </button>
      </div>
      <p className="mt-2 px-1 text-xs text-slate-400">{notice}</p>
    </footer>
  );
}
