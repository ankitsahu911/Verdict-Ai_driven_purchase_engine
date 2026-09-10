"use client";

import React from "react";
import {
  Layers,
  Copy,
  Calendar,
  Coins,
  Leaf,
  Info,
  AlertTriangle,
  CheckCircle2,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { DecisionSummaryMetricsData } from "@/lib/api";

interface DecisionSummaryPanelProps {
  metrics?: DecisionSummaryMetricsData | null;
  className?: string;
  variant?: "full" | "compact";
  columns?: 2 | 3 | 5 | "auto";
  title?: string;
}

export function DecisionSummaryPanel({
  metrics,
  className = "",
  variant = "full",
  columns = "auto",
  title = "5-Metric Decision Summary",
}: DecisionSummaryPanelProps) {
  if (!metrics) return null;

  const isCompact = variant === "compact";

  // Polarity-appropriate styles for duplicate risk
  const dupRisk = metrics.duplicate_risk;
  const isHighDup = dupRisk >= 70;
  const isModDup = dupRisk >= 35;
  const dupBadgeVariant: "buy" | "consider" | "skip" = isHighDup
    ? "skip"
    : isModDup
    ? "consider"
    : "buy";

  // Sustainability tier styling
  const tier = metrics.sustainability_tier;
  const isLowerImpact = tier.toLowerCase().includes("lower");
  const isHigherImpact = tier.toLowerCase().includes("higher");
  const sustBadgeVariant: "buy" | "consider" | "neutral" = isLowerImpact
    ? "buy"
    : isHigherImpact
    ? "consider"
    : "neutral";

  return (
    <div className={`space-y-3 ${className}`}>
      <div className="flex items-center justify-between">
        <div className="flex items-center gap-2">
          <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
            {title}
          </span>
        </div>
        <span className="text-[10px] text-muted-foreground font-medium">
          M31 Summary Panel
        </span>
      </div>

      <div
        className={`grid gap-2.5 ${
          columns === 2
            ? "grid-cols-1 sm:grid-cols-2"
            : columns === 3
            ? "grid-cols-1 sm:grid-cols-3"
            : columns === 5
            ? "grid-cols-2 sm:grid-cols-5"
            : isCompact
            ? "grid-cols-2 sm:grid-cols-3 xl:grid-cols-5"
            : "grid-cols-1 sm:grid-cols-2 lg:grid-cols-5"
        }`}
      >
        {/* 1. Versatility */}
        <div className="p-3 rounded-2xl border bg-card shadow-xs flex flex-col justify-between space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
              Versatility
            </span>
            <Layers className="h-4 w-4 text-blue-500" />
          </div>
          <div>
            <div className="font-extrabold text-base text-foreground">
              {metrics.versatility_outfits_count > 0
                ? `${metrics.versatility_outfits_count} Outfits`
                : `${metrics.versatility.toFixed(0)}/100`}
            </div>
            <p className="text-[11px] text-muted-foreground truncate">
              {metrics.versatility.toFixed(1)}/100 pairing score
            </p>
          </div>
        </div>

        {/* 2. Duplicate Risk (IMPORTANT: NON-INVERTED) */}
        <div className="p-3 rounded-2xl border bg-card shadow-xs flex flex-col justify-between space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
              Duplicate Risk
            </span>
            <span className="text-[9px] text-muted-foreground font-mono hidden sm:inline" title="Inverted on Buy Score radar as Uniqueness">
              (100% − Uniq)
            </span>
            <Copy className="h-4 w-4 text-purple-500" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-extrabold text-base text-foreground font-mono">
                {metrics.duplicate_risk.toFixed(1)}%
              </span>
              <Badge variant={dupBadgeVariant} className="text-[9px] px-1.5 py-0 font-bold">
                {isHighDup ? "High" : isModDup ? "Moderate" : "Low"}
              </Badge>
            </div>
            <p
              className="text-[11px] text-muted-foreground truncate"
              title={`${metrics.duplicate_risk_label} — direct closet overlap (inverse of Uniqueness score: ${Math.round(Math.max(0, 100 - metrics.duplicate_risk))}/100)`}
            >
              {metrics.duplicate_risk_label}
            </p>
          </div>
        </div>

        {/* 3. Seasonality */}
        <div className="p-3 rounded-2xl border bg-card shadow-xs flex flex-col justify-between space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
              Seasonality
            </span>
            <Calendar className="h-4 w-4 text-amber-500" />
          </div>
          <div>
            <div className="font-extrabold text-base text-foreground truncate">
              {metrics.seasonality >= 80 ? "In-Season" : metrics.seasonality >= 50 ? "Upcoming" : "Off-Season"}
            </div>
            <p className="text-[11px] text-muted-foreground truncate" title={metrics.seasonality_label}>
              {metrics.seasonality.toFixed(0)}/100 utility score
            </p>
          </div>
        </div>

        {/* 4. Cost-per-Wear */}
        <div className="p-3 rounded-2xl border bg-card shadow-xs flex flex-col justify-between space-y-1.5">
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
              Cost-Per-Wear
            </span>
            <Coins className="h-4 w-4 text-emerald-500" />
          </div>
          <div>
            <div className="font-extrabold text-base text-foreground font-mono">
              {metrics.cost_per_wear_formatted}
            </div>
            <p className="text-[11px] text-muted-foreground truncate">
              Raw currency/wear baseline
            </p>
          </div>
        </div>

        {/* 5. Sustainability Tier */}
        <div
          className={`p-3 rounded-2xl border bg-card shadow-xs flex flex-col justify-between space-y-1.5 ${
            columns === 2 ? "sm:col-span-2" : ""
          }`}
        >
          <div className="flex items-center justify-between">
            <span className="text-[11px] font-bold uppercase tracking-wider text-muted-foreground">
              Sustainability
            </span>
            <Leaf className="h-4 w-4 text-emerald-600 dark:text-emerald-400" />
          </div>
          <div>
            <div className="flex items-center gap-1.5">
              <span className="font-extrabold text-sm text-foreground truncate">
                {metrics.sustainability_tier}
              </span>
              <Badge variant={sustBadgeVariant} className="text-[9px] px-1.5 py-0 font-bold">
                Estimate
              </Badge>
            </div>
            <p
              className="text-[10px] text-muted-foreground line-clamp-1 italic"
              title={metrics.sustainability_reason || "Rough material estimate based on fabric composition. Not a certified eco-rating."}
            >
              Rough material estimate
            </p>
          </div>
        </div>
      </div>
    </div>
  );
}
