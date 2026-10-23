"use client";

import { usePathname } from "next/navigation";
import { DashboardSidebar } from "@/components/dashboard/sidebar";

export default function DashboardLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  const pathname = usePathname();
  const isChatRoute =
    pathname === "/dashboard/chat" || pathname?.startsWith("/dashboard/chat/");

  if (isChatRoute) {
    // Chat workspace manages its own 3-column resizable layout
    return (
      <div className="h-dvh w-full overflow-hidden bg-slate-50 dark:bg-zinc-950 text-slate-900 dark:text-zinc-100 flex flex-col transition-colors">
        {children}
      </div>
    );
  }

  return (
    <div className="flex min-h-screen bg-slate-50 dark:bg-zinc-950 text-slate-900 dark:text-zinc-100 transition-colors">
      {/* Sidebar navigation */}
      <DashboardSidebar />

      {/* Main content pane */}
      <div className="flex-1 flex flex-col min-w-0">{children}</div>
    </div>
  );
}
