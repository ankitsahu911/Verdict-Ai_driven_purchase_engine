"use client";

import React, { useState } from "react";
import { ShieldCheck, AlertTriangle, HelpCircle, Info, Sparkles } from "lucide-react";
import { Badge } from "@/components/ui/badge";
import type { ConfidenceResultData } from "@/lib/api";

interface ConfidenceBadgeProps {
  confidence?: ConfidenceResultData | null;
  size?: "sm" | "md" | "lg";
  className?: string;
}

export function ConfidenceBadge({
  confidence,
  size = "sm",
  className = "",
}: ConfidenceBadgeProps) {
  const [isOpen, setIsOpen] = useState(false);

  if (!confidence || !confidence.level) {
    return null;
  }

  const level = confidence.level.toLowerCase();
  const reasoning = confidence.reasoning || "";

  let badgeVariant: "buy" | "consider" | "skip" | "neutral" = "neutral";
  let Icon = Info;
  let label = "Confidence";

  if (level === "high") {
    badgeVariant = "buy";
    Icon = ShieldCheck;
    label = "High Confidence";
  } else if (level === "medium") {
    badgeVariant = "consider";
    Icon = HelpCircle;
    label = "Medium Confidence";
  } else if (level === "low") {
    badgeVariant = "skip";
    Icon = AlertTriangle;
    label = "Low Confidence";
  }

  const sizeClasses =
    size === "lg"
      ? "text-sm px-3 py-1.5 gap-2"
      : size === "md"
      ? "text-xs px-2.5 py-1 gap-1.5"
      : "text-[11px] px-2 py-0.5 gap-1.5";

  const iconSizeClass =
    size === "lg" ? "h-4 w-4" : size === "md" ? "h-3.5 w-3.5" : "h-3 w-3";

  return (
    <div className="relative inline-block">
      <Badge
        variant={badgeVariant}
        onClick={(e) => {
          e.stopPropagation();
          setIsOpen(!isOpen);
        }}
        onMouseEnter={() => setIsOpen(true)}
        onMouseLeave={() => setIsOpen(false)}
        className={`cursor-pointer transition-all select-none flex items-center font-bold shadow-xs ${sizeClasses} ${className}`}
      >
        <Icon className={iconSizeClass} />
        <span>{label}</span>
      </Badge>

      {/* Hover / Click Detail Popover - Responsive mobile clamp */}
      {isOpen && (
        <div
          onClick={(e) => e.stopPropagation()}
          className="absolute z-50 bottom-full left-1/2 -translate-x-1/2 mb-2 w-[calc(100vw-32px)] max-w-xs sm:w-72 p-3.5 rounded-2xl bg-popover/95 backdrop-blur-md border border-border shadow-xl text-left text-xs text-popover-foreground animate-in fade-in zoom-in-95 duration-150"
        >
          <div className="flex items-center gap-1.5 font-bold pb-1.5 border-b border-border/50 text-[11px] uppercase tracking-wider text-muted-foreground">
            <Icon className="h-3.5 w-3.5 text-foreground" />
            <span>Confidence Signal Breakdown</span>
          </div>

          <p className="mt-2 text-xs leading-relaxed text-foreground font-medium">
            {reasoning}
          </p>

          <div className="mt-2 pt-2 border-t border-border/50 flex items-center justify-between text-[10px] text-muted-foreground">
            <span>Formula: M29 Deterministic</span>
            <span className="capitalize font-mono font-bold">{level}</span>
          </div>
        </div>
      )}
    </div>
  );
}
