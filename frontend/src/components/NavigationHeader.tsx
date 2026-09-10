"use client";

import React from "react";
import Link from "next/link";
import { usePathname } from "next/navigation";
import {
  Shirt,
  Compass,
  LayoutDashboard,
  Sparkles,
  FlaskConical,
  Scale,
  Bot,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";

interface NavigationHeaderProps {
  currentSubtitle?: string;
  badgeText?: string;
  className?: string;
}

const NAV_ITEMS = [
  { href: "/wardrobe", label: "Wardrobe", icon: Compass },
  { href: "/candidates", label: "Evaluate Item", icon: Shirt },
  { href: "/verdict-test", label: "Verdict Visualizer", icon: Sparkles },
  { href: "/what-if", label: "What-If Lab", icon: FlaskConical },
  { href: "/opportunity-cost", label: "Opportunity Cost", icon: Scale },
  { href: "/stylist", label: "Stylist Chat", icon: Bot },
  { href: "/dashboard", label: "Dashboard", icon: LayoutDashboard },
];

export function NavigationHeader({
  currentSubtitle,
  badgeText,
  className = "",
}: NavigationHeaderProps) {
  const pathname = usePathname();

  return (
    <header
      className={`sticky top-0 z-30 border-b bg-background/90 backdrop-blur-md ${className}`}
    >
      <div className="mx-auto flex h-16 max-w-7xl items-center justify-between px-4 sm:px-6 lg:px-8 gap-3">
        {/* Brand Logo & Subtitle */}
        <Link
          href="/dashboard"
          className="flex items-center gap-2.5 shrink-0 group select-none"
        >
          <div className="flex h-9 w-9 items-center justify-center rounded-xl bg-primary text-primary-foreground font-black text-lg shadow-sm transition-transform group-hover:scale-105">
            V
          </div>
          <div>
            <span className="font-extrabold text-base tracking-tight block text-foreground leading-none">
              Verdict
            </span>
            <span className="text-[10px] text-muted-foreground block font-medium mt-0.5">
              {currentSubtitle || "AI Purchase Engine"}
            </span>
          </div>
          {badgeText && (
            <Badge
              variant="outline"
              className="ml-1.5 hidden md:inline-flex bg-primary/5 text-primary border-primary/20 text-[11px] font-semibold"
            >
              {badgeText}
            </Badge>
          )}
        </Link>

        {/* Navigation Links - Horizontal scroll on mobile */}
        <nav className="flex items-center gap-1 sm:gap-1.5 overflow-x-auto py-1 scrollbar-none max-w-[calc(100vw-140px)] sm:max-w-none">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                className={`flex items-center gap-1.5 px-2.5 sm:px-3 py-1.5 rounded-lg text-xs font-medium whitespace-nowrap transition-colors shrink-0 ${
                  isActive
                    ? "bg-primary/10 text-primary font-bold shadow-2xs"
                    : "text-muted-foreground hover:text-foreground hover:bg-muted/60"
                }`}
              >
                <Icon className={`h-3.5 w-3.5 ${isActive ? "text-primary" : "text-muted-foreground"}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>
      </div>
    </header>
  );
}
