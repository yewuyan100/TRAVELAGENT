import type { PropsWithChildren } from "react";
import { Header } from "@/components/layout/Header";
import { Sidebar } from "@/components/layout/Sidebar";

export function AppLayout({ children }: PropsWithChildren) {
  return (
    <div className="flex h-svh overflow-hidden bg-slate-50 text-slate-950">
      <Sidebar />
      <div className="flex min-w-0 flex-1 flex-col">
        <Header />
        <main className="flex min-h-0 flex-1 flex-col">{children}</main>
      </div>
    </div>
  );
}
