"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { cn } from "@/lib/utils";
import {
  LayoutDashboard,
  Package,
  ClipboardList,
  Wallet,
  ShieldAlert,
  Store,
  FileText,
  Settings,
  LogOut,
  Puzzle,
} from "lucide-react";

const navItems = [
  { href: "/dashboard/overview", label: "概览", icon: LayoutDashboard },
  { href: "/dashboard/products", label: "商品管理", icon: Package },
  { href: "/dashboard/extension-install", label: "采集插件", icon: Puzzle },
  { href: "/dashboard/audit", label: "审核中心", icon: ClipboardList },
  { href: "/dashboard/finance", label: "财务看板", icon: Wallet },
  { href: "/dashboard/risk", label: "风控日志", icon: ShieldAlert },
  { href: "/dashboard/shops", label: "店铺管理", icon: Store },
  { href: "/dashboard/listings", label: "上架记录", icon: FileText },
  { href: "/dashboard/settings", label: "系统设置", icon: Settings },
];

export function Sidebar() {
  const pathname = usePathname();

  return (
    <aside className="fixed left-0 top-0 z-40 h-screen w-64 border-r bg-background">
      {/* Logo */}
      <div className="flex h-16 items-center border-b px-6">
        <Link href="/dashboard/overview" className="flex items-center gap-2">
          <span className="text-xl font-bold text-primary">pipixia</span>
        </Link>
      </div>

      {/* Navigation */}
      <nav className="flex-1 space-y-1 px-3 py-4">
        {navItems.map((item) => {
          const isActive = pathname === item.href;
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-3 rounded-lg px-3 py-2.5 text-sm transition-colors",
                isActive
                  ? "bg-accent text-accent-foreground font-medium"
                  : "text-muted-foreground hover:bg-accent/50 hover:text-foreground"
              )}
            >
              <item.icon className="h-4 w-4" />
              {item.label}
            </Link>
          );
        })}
      </nav>

      {/* Footer */}
      <div className="border-t px-3 py-4">
        <button
          className="flex w-full items-center gap-3 rounded-lg px-3 py-2.5 text-sm text-muted-foreground transition-colors hover:bg-destructive/10 hover:text-destructive"
          onClick={() => {
            localStorage.removeItem("access_token");
            window.location.href = "/login";
          }}
        >
          <LogOut className="h-4 w-4" />
          退出登录
        </button>
      </div>
    </aside>
  );
}
