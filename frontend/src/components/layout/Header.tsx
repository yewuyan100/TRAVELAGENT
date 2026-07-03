import { Menu, PanelLeftClose, PanelLeftOpen, Settings } from "lucide-react";
import { useSidebarStore } from "@/store/useSidebarStore";

export function Header() {
  const { isOpen, toggleSidebar, toggleMobileSidebar } = useSidebarStore();

  return (
    <header className="flex h-14 shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4">
      <div className="flex items-center gap-2">
        <button
          type="button"
          className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 hover:bg-slate-100 md:hidden"
          onClick={toggleMobileSidebar}
          aria-label="打开移动端菜单"
        >
          <Menu className="h-4 w-4" />
        </button>
        <button
          type="button"
          className="hidden h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 hover:bg-slate-100 md:inline-flex"
          onClick={toggleSidebar}
          aria-label={isOpen ? "折叠侧边栏" : "展开侧边栏"}
        >
          {isOpen ? <PanelLeftClose className="h-4 w-4" /> : <PanelLeftOpen className="h-4 w-4" />}
        </button>
        <div>
          <h1 className="text-base font-semibold leading-tight text-slate-950">智能旅游 RAG Agent</h1>
          <p className="text-xs text-slate-500">Local Agent Demo</p>
        </div>
      </div>
      <button
        type="button"
        className="inline-flex h-9 w-9 items-center justify-center rounded-md border border-slate-200 text-slate-600 hover:bg-slate-100"
        aria-label="设置"
      >
        <Settings className="h-4 w-4" />
      </button>
    </header>
  );
}
