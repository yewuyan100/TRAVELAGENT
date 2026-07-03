import { useEffect, useRef } from "react";
import { MessageItem } from "@/components/chat/MessageItem";
import { useChatStore } from "@/store/useChatStore";

export function MessageList() {
  const messages = useChatStore((state) => state.messages);
  const bottomRef = useRef<HTMLDivElement | null>(null);

  useEffect(() => {
    bottomRef.current?.scrollIntoView({ behavior: "smooth", block: "end" });
  }, [messages]);

  return (
    <section className="min-h-0 flex-1 overflow-y-auto px-4 py-6">
      <div className="mx-auto flex max-w-4xl flex-col gap-5">
        {messages.length === 0 ? (
          <div className="rounded-xl border border-dashed border-slate-300 bg-white p-8 text-center text-sm text-slate-500">
            你好，我可以帮你查询城市攻略、天气、路线规划或旅行建议。
          </div>
        ) : (
          messages.map((message) => <MessageItem key={message.id} message={message} />)
        )}
        <div ref={bottomRef} />
      </div>
    </section>
  );
}
