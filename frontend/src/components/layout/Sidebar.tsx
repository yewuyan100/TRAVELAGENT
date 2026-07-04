import { CalendarDays, Clock3, MessageSquare, MessageSquarePlus, Sparkles, X } from "lucide-react";
import { useChatStore } from "@/store/useChatStore";
import { useSidebarStore } from "@/store/useSidebarStore";
import { cn } from "@/lib/utils";

const navItems = [
  { label: "对话", icon: MessageSquare },
  { label: "行程", icon: CalendarDays },
];

function timeLabel(timestamp: number) {
  const now = Date.now();
  const diff = now - timestamp;
  if (diff < 24 * 60 * 60 * 1000) {
    return new Date(timestamp).toLocaleTimeString("zh-CN", { hour: "2-digit", minute: "2-digit" });
  }
  if (diff < 7 * 24 * 60 * 60 * 1000) {
    return `${Math.ceil(diff / (24 * 60 * 60 * 1000))}天前`;
  }
  return new Date(timestamp).toLocaleDateString("zh-CN", { month: "2-digit", day: "2-digit" });
}

export function Sidebar() {
  const { beginNewSession, histories, restoreConversation, activeSessionId } = useChatStore();
  const { isMobileOpen, closeMobileSidebar } = useSidebarStore();

  const content = (
    <div className="flex h-full flex-col border-r border-emerald-100 bg-emerald-50/80 text-slate-950">
      <div className="flex items-center justify-between px-5 py-5">
        <div className="flex min-w-0 items-center gap-3">
          <span className="inline-flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-emerald-600 text-white shadow-sm">
            <Sparkles className="h-5 w-5" />
          </span>
          <div className="min-w-0">
            <div className="truncate text-lg font-semibold">AI Travel Agent</div>
            <div className="text-xs text-slate-500">旅行规划工作台</div>
          </div>
        </div>
        <button
          type="button"
          className="inline-flex h-9 w-9 items-center justify-center rounded-md text-slate-500 hover:bg-white md:hidden"
          onClick={closeMobileSidebar}
          aria-label="关闭菜单"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="px-4">
        <button
          type="button"
          className="flex h-12 w-full items-center justify-center gap-2 rounded-lg bg-emerald-700 px-4 text-sm font-semibold text-white shadow-sm transition hover:bg-emerald-800 active:scale-[0.99]"
          onClick={() => {
            beginNewSession();
            closeMobileSidebar();
          }}
        >
          <MessageSquarePlus className="h-4 w-4" />
          新建对话
        </button>
      </div>

      <div className="mt-6 space-y-1 px-3">
        {navItems.map((item) => {
          const Icon = item.icon;
          return (
            <div key={item.label} className="flex w-full items-center gap-3 rounded-lg px-3 py-3">
              <span className="inline-flex h-9 w-9 shrink-0 items-center justify-center rounded-lg bg-white text-emerald-700">
                <Icon className="h-4 w-4" />
              </span>
              <span className="text-sm font-semibold">{item.label}</span>
            </div>
          );
        })}
      </div>

      <div className="mt-5 min-h-0 flex-1 px-4">
        <div className="mb-3 flex items-center justify-between rounded-lg bg-emerald-100/80 px-3 py-3 text-sm font-semibold text-emerald-900">
          <span className="inline-flex items-center gap-2">
            <Clock3 className="h-4 w-4" />
            对话历史
          </span>
        </div>
        <div className="space-y-1 overflow-y-auto pr-1">
          {histories.length === 0 ? (
            <div className="rounded-lg border border-dashed border-emerald-200 bg-white/60 px-3 py-4 text-xs leading-5 text-slate-500">
              本地历史会保存在当前浏览器，不会同步给其他用户。
            </div>
          ) : (
            histories.map((item) => (
              <button
                key={item.id}
                type="button"
                className={cn(
                  "flex w-full items-center justify-between gap-3 rounded-lg px-3 py-2 text-left text-sm transition",
                  item.id === activeSessionId ? "bg-emerald-100 text-emerald-900" : "hover:bg-white"
                )}
                onClick={() => {
                  restoreConversation(item.id);
                  closeMobileSidebar();
                }}
              >
                <span className="min-w-0 truncate">{item.title}</span>
                <span className="shrink-0 text-xs text-slate-400">{timeLabel(item.updatedAt)}</span>
              </button>
            ))
          )}
        </div>
      </div>

      <div className="m-4 rounded-lg bg-white p-4 text-xs leading-5 text-slate-500 shadow-sm">
        当前版本聚焦问答、行程建议和 Agent 执行过程展示。
      </div>
    </div>
  );

  return (
    <>
      <aside className="hidden w-72 shrink-0 md:block">{content}</aside>
      {isMobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-slate-950/35"
            onClick={closeMobileSidebar}
            aria-label="关闭侧边栏遮罩"
          />
          <aside className="absolute inset-y-0 left-0 w-72 shadow-xl">{content}</aside>
        </div>
      )}
    </>
  );
}
