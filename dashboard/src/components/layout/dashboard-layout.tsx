"use client";

import { Sidebar } from "./sidebar";
import { Topbar } from "./topbar";

interface DashboardLayoutProps {
  children: React.ReactNode;
}

export function DashboardLayout({ children }: DashboardLayoutProps) {
  return (
    <div className="min-h-screen bg-background">
      <Sidebar />
      <div className="ml-64">
        <Topbar />
        <main className="p-6">{children}</main>
      </div>
    </div>
  );
}
