import type { PropsWithChildren } from "react";
import { RightPanel } from "@/components/layout/RightPanel";
import { Sidebar } from "@/components/layout/Sidebar";
import { TopBar } from "@/components/layout/TopBar";

export function AppLayout({ children }: PropsWithChildren) {
  return (
    <div className="flex h-svh overflow-hidden bg-white text-slate-950">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <TopBar />
        <main className="flex min-h-0 flex-1">
          <div className="flex min-w-0 flex-1 flex-col">{children}</div>
          <RightPanel />
        </main>
      </div>
    </div>
  );
}
