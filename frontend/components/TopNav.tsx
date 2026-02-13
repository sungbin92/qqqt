"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  LayoutDashboard,
  FlaskConical,
  ListOrdered,
  Settings2,
  GitCompareArrows,
} from "lucide-react";
import { cn } from "@/lib/utils";

const navItems = [
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
  { href: "/backtest", label: "Backtest", icon: FlaskConical },
  { href: "/strategies", label: "Strategies", icon: ListOrdered },
  { href: "/compare", label: "Compare", icon: GitCompareArrows },
  { href: "/optimize", label: "Optimize", icon: Settings2 },
];

export function TopNav() {
  const pathname = usePathname();

  return (
    <header className="sticky top-0 z-50 flex h-14 items-center border-b bg-card px-4">
      <Link href="/dashboard" className="mr-6 text-lg font-bold md:hidden">
        QB
      </Link>
      <nav className="flex items-center gap-1 md:hidden">
        {navItems.map((item) => {
          const Icon = item.icon;
          const active = pathname.startsWith(item.href);
          return (
            <Link
              key={item.href}
              href={item.href}
              className={cn(
                "flex items-center gap-1.5 rounded-md px-2.5 py-1.5 text-sm font-medium transition-colors",
                active
                  ? "bg-accent text-accent-foreground"
                  : "text-muted-foreground hover:text-foreground"
              )}
            >
              <Icon className="h-4 w-4" />
              <span className="hidden sm:inline">{item.label}</span>
            </Link>
          );
        })}
      </nav>
      <div className="ml-auto text-sm text-muted-foreground">
        Quant Backtest System
      </div>
    </header>
  );
}
