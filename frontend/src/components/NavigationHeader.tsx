"use client";

import React from "react";
import Link from "next/link";
import { usePathname, useRouter } from "next/navigation";
import {
  Home,
  Shirt,
  Compass,
  LayoutDashboard,
  Sparkles,
  FlaskConical,
  Scale,
  Bot,
  Sun,
  Moon,
  BookOpen,
  LogOut,
  User,
  Ruler,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { useTheme } from "@/contexts/ThemeContext";
import { useAuth } from "@/contexts/AuthContext";

interface NavigationHeaderProps {
  currentSubtitle?: string;
  badgeText?: string;
  className?: string;
}

const NAV_ITEMS = [
  { href: "/", label: "Home", icon: Home },
  { href: "/wardrobe", label: "Wardrobe", icon: Compass },
  { href: "/candidates", label: "Evaluate Item", icon: Shirt },
  { href: "/fitting-room", label: "Size & Fit Profile", icon: Ruler },
  { href: "/blog", label: "Style Guide", icon: BookOpen },
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
  const router = useRouter();
  const { theme, toggleTheme } = useTheme();
  const { user, logout } = useAuth();

  function handleLogout() {
    logout();
    router.push("/login");
  }

  return (
    <header
      className={`sticky top-0 z-40 border-b border-border/80 bg-background/95 backdrop-blur-xl transition-colors duration-200 ${className}`}
    >
      <div className="flex h-16 w-full items-center justify-between px-3 sm:px-6 lg:px-8 gap-2 sm:gap-4">
        {/* Brand Logo & Subtitle */}
        <Link
          href="/"
          prefetch={true}
          className="flex items-center gap-2.5 shrink-0 group select-none"
        >
          <div className="flex h-10 w-10 items-center justify-center rounded-2xl bg-neutral-900 text-white font-serif font-bold text-xl shadow-md transition-transform group-hover:scale-105 duration-200 dark:bg-white dark:text-neutral-900">
            V
          </div>
          <div>
            <div className="flex items-center gap-2">
              <span className="font-serif font-bold text-lg sm:text-xl tracking-tight block text-foreground leading-none">
                Verdict
              </span>
              {badgeText && (
                <Badge
                  variant="outline"
                  className="hidden 2xl:inline-flex bg-muted/60 text-foreground border-border text-[10px] font-bold tracking-wider uppercase px-2 py-0.5"
                >
                  {badgeText}
                </Badge>
              )}
            </div>
            <span className="text-[10px] text-muted-foreground block font-semibold mt-0.5 tracking-wider uppercase truncate max-w-[140px] sm:max-w-none">
              {currentSubtitle || "Luxury Purchase Engine"}
            </span>
          </div>
        </Link>

        {/* Navigation Links — Bigger Buttons & Crisp Font Sizes */}
        <nav className="flex items-center gap-1 sm:gap-2 overflow-x-auto py-1 scrollbar-none max-w-[calc(100vw-240px)] sm:max-w-none">
          {NAV_ITEMS.map((item) => {
            const Icon = item.icon;
            const isActive = pathname === item.href;
            return (
              <Link
                key={item.href}
                href={item.href}
                prefetch={true}
                className={`flex items-center gap-2 px-3.5 py-2 rounded-xl text-xs sm:text-sm font-semibold tracking-wide whitespace-nowrap transition-all shrink-0 cursor-pointer ${
                  isActive
                    ? "bg-neutral-900 text-white shadow-sm dark:bg-white dark:text-neutral-900 font-bold"
                    : "text-muted-foreground hover:text-foreground hover:bg-neutral-200/50 dark:hover:bg-neutral-800/80"
                }`}
              >
                <Icon className={`h-4 w-4 ${isActive ? "text-white dark:text-neutral-900" : "text-muted-foreground"}`} />
                <span>{item.label}</span>
              </Link>
            );
          })}
        </nav>

        {/* Controls: User Auth, Theme Toggle */}
        <div className="flex items-center gap-2 shrink-0">
          {/* User Status / Logout */}
          {user ? (
            <div className="flex items-center gap-1 sm:gap-2">
              <div className="hidden lg:flex items-center gap-1.5 px-2.5 py-1 rounded-xl bg-muted/40 border border-border text-xs font-semibold text-foreground">
                <User className="h-3.5 w-3.5 text-muted-foreground" />
                <span className="max-w-[110px] truncate">{user.email.split("@")[0]}</span>
              </div>
              <Button
                variant="outline"
                size="sm"
                onClick={handleLogout}
                title="Log out"
                className="h-10 px-3 text-xs font-bold rounded-xl border-border hover:bg-destructive/10 hover:text-destructive hover:border-destructive/30 transition-all flex items-center gap-1.5 cursor-pointer"
              >
                <LogOut className="h-3.5 w-3.5" />
                <span className="hidden md:inline">Sign Out</span>
              </Button>
            </div>
          ) : (
            <Link href="/login" prefetch={true}>
              <Button
                size="sm"
                className="h-10 px-4 text-xs font-bold rounded-xl bg-neutral-900 text-white hover:bg-black dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-100 shadow-sm"
              >
                Sign In
              </Button>
            </Link>
          )}

          {/* Theme Toggle Button */}
          <Button
            variant="outline"
            size="sm"
            onClick={toggleTheme}
            aria-label={`Switch to ${theme === "dark" ? "light" : "dark"} mode`}
            className="h-10 px-3.5 rounded-xl border-border bg-card/80 backdrop-blur-md text-foreground font-semibold hover:border-foreground/50 transition-all flex items-center gap-2 cursor-pointer shadow-xs"
          >
            {theme === "dark" ? (
              <>
                <Sun className="h-4 w-4 text-amber-500 transition-transform duration-300 hover:rotate-90" />
                <span className="text-xs font-bold hidden md:inline tracking-wide">Light</span>
              </>
            ) : (
              <>
                <Moon className="h-4 w-4 text-neutral-800 transition-transform duration-300 hover:-rotate-12" />
                <span className="text-xs font-bold hidden md:inline tracking-wide">Dark</span>
              </>
            )}
          </Button>
        </div>
      </div>
    </header>
  );
}
