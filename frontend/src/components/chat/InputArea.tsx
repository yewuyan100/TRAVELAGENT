import { useState } from "react";
import { SendHorizontal } from "lucide-react";
import { sendStreamingChat } from "@/api/chatService";
import { useChatStore } from "@/store/useChatStore";

export function InputArea() {
  const [value, setValue] = useState("");
  const isStreaming = useChatStore((state) => state.isStreaming);

  async function submit() {
    const query = value.trim();
    if (!query || isStreaming) return;
    setValue("");

    try {
      await sendStreamingChat(query);
    } catch {
      // chatService already updates the assistant placeholder with failed status.
    }
  }

  return (
    <footer className="shrink-0 border-t border-slate-200 bg-white px-4 py-4">
      <div className="mx-auto flex max-w-4xl gap-3">
        <textarea
          value={value}
          disabled={isStreaming}
          rows={1}
          placeholder="问我城市攻略、实时天气、路线规划或旅行建议..."
          className="max-h-40 min-h-12 flex-1 resize-y rounded-xl border border-slate-300 bg-white px-4 py-3 text-sm leading-6 outline-none transition focus:border-slate-500 disabled:cursor-not-allowed disabled:bg-slate-50"
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
          className="inline-flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-slate-950 text-white transition hover:bg-slate-800 disabled:cursor-not-allowed disabled:bg-slate-300"
          aria-label="发送"
        >
          <SendHorizontal className="h-5 w-5" />
        </button>
      </div>
      <div className="mx-auto mt-2 max-w-4xl text-xs text-slate-400">
        Enter 发送，Shift + Enter 换行。当前默认请求 /api/chat/stream。
      </div>
    </footer>
  );
}
