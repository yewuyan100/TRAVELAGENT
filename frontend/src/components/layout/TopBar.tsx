import { useEffect, useState } from "react";
import { ChevronDown, Menu } from "lucide-react";
import { getHealth } from "@/api/chat";
import { useSidebarStore } from "@/store/useSidebarStore";

type ServiceState = "checking" | "online" | "offline";

export function TopBar() {
  const { toggleMobileSidebar } = useSidebarStore();
  const [serviceState, setServiceState] = useState<ServiceState>("checking");

  useEffect(() => {
    let cancelled = false;

    getHealth()
      .then((data) => {
        if (!cancelled) setServiceState(data.status === "ok" ? "online" : "offline");
      })
      .catch(() => {
        if (!cancelled) setServiceState("offline");
      });

    return () => {
      cancelled = true;
    };
  }, []);

  const statusText = serviceState === "online" ? "服务正常" : serviceState === "checking" ? "检查中" : "服务异常";

  return (
    <header className="flex h-[72px] shrink-0 items-center justify-between border-b border-slate-200 bg-white px-4 md:px-8">
      <div className="flex min-w-0 items-center gap-3">
        <button
          type="button"
          className="inline-flex h-10 w-10 items-center justify-center rounded-lg border border-slate-200 text-slate-600 hover:bg-slate-50 md:hidden"
          onClick={toggleMobileSidebar}
          aria-label="打开菜单"
        >
          <Menu className="h-5 w-5" />
        </button>
        <div className="min-w-0">
          <h1 className="truncate text-xl font-semibold tracking-normal text-slate-950">您好，旅行者</h1>
          <p className="truncate text-sm text-slate-500">提问后可以看到回答、工具调用和知识召回过程</p>
        </div>
      </div>

      <div className="flex shrink-0 items-center gap-3">
        <button
          type="button"
          className="hidden items-center gap-2 rounded-full bg-emerald-50 px-4 py-2 text-sm font-medium text-emerald-700 sm:inline-flex"
          onClick={() => window.alert(serviceState === "online" ? "后端服务连接正常。" : "后端服务暂时不可用，请检查 FastAPI 是否启动。")}
        >
          <span className={`h-2 w-2 rounded-full ${serviceState === "online" ? "bg-emerald-500" : "bg-amber-500"}`} />
          {statusText}
        </button>

        <button
          type="button"
          className="inline-flex items-center gap-2 rounded-full px-1.5 py-1.5 hover:bg-slate-50"
          onClick={() => window.alert("当前以本地旅行者身份使用，暂未接入登录系统。")}
          aria-label="用户菜单"
        >
          <span className="h-10 w-10 overflow-hidden rounded-full bg-[linear-gradient(135deg,#d1fae5,#bae6fd)]" />
          <ChevronDown className="hidden h-4 w-4 text-slate-500 sm:block" />
        </button>
      </div>
    </header>
  );
}
