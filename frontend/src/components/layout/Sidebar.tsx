import { MessageSquarePlus, Plane, X } from "lucide-react";
import { useChatStore } from "@/store/useChatStore";
import { useSidebarStore } from "@/store/useSidebarStore";
import { cn } from "@/lib/utils";

const histories = [
  "成都慢旅行建议",
  "北京三日游路线",
  "上海购物与文化游",
  "大阪京都行程安排",
];

export function Sidebar() {
  const { resetChat } = useChatStore();
  const {
    isOpen,
    isMobileOpen,
    closeMobileSidebar,
  } = useSidebarStore();

  const sidebarContent = (
    <div className="flex h-full flex-col border-r border-slate-200 bg-white">
      <div className="flex h-14 items-center justify-between px-4">
        <div className="flex items-center gap-2 font-semibold text-slate-950">
          <span className="inline-flex h-8 w-8 items-center justify-center rounded-md bg-slate-950 text-white">
            <Plane className="h-4 w-4" />
          </span>
          <span className={cn(!isOpen && "md:hidden")}>AI Travel Agent</span>
        </div>
        <button
          type="button"
          className="inline-flex h-8 w-8 items-center justify-center rounded-md text-slate-500 hover:bg-slate-100 md:hidden"
          onClick={closeMobileSidebar}
          aria-label="关闭菜单"
        >
          <X className="h-4 w-4" />
        </button>
      </div>

      <div className="px-3 py-3">
        <button
          type="button"
          className="flex w-full items-center justify-center gap-2 rounded-md bg-slate-950 px-3 py-2 text-sm font-medium text-white hover:bg-slate-800"
          onClick={() => {
            resetChat();
            closeMobileSidebar();
          }}
        >
          <MessageSquarePlus className="h-4 w-4" />
          <span className={cn(!isOpen && "md:hidden")}>New Chat</span>
        </button>
      </div>

      <div className={cn("min-h-0 flex-1 px-3", !isOpen && "md:hidden")}>
        <div className="mb-2 px-1 text-xs font-medium uppercase tracking-wide text-slate-500">History</div>
        <div className="space-y-1">
          {histories.map((item) => (
            <button
              key={item}
              type="button"
              className="w-full truncate rounded-md px-3 py-2 text-left text-sm text-slate-600 hover:bg-slate-100"
            >
              {item}
            </button>
          ))}
        </div>
      </div>
    </div>
  );

  return (
    <>
      <aside className={cn("hidden shrink-0 transition-all duration-200 md:block", isOpen ? "w-72" : "w-16")}>
        {sidebarContent}
      </aside>
      {isMobileOpen && (
        <div className="fixed inset-0 z-40 md:hidden">
          <button
            type="button"
            className="absolute inset-0 bg-slate-950/35"
            onClick={closeMobileSidebar}
            aria-label="关闭侧边栏遮罩"
          />
          <aside className="absolute inset-y-0 left-0 w-72 shadow-xl">{sidebarContent}</aside>
        </div>
      )}
    </>
  );
}
