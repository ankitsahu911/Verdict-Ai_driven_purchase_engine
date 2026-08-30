"use client";

import React, { useEffect, useState } from "react";
import { motion } from "framer-motion";
import {
  ResponsiveContainer,
  RadarChart,
  PolarGrid,
  PolarAngleAxis,
  PolarRadiusAxis,
  Radar,
  Tooltip,
} from "recharts";
import {
  CheckCircle2,
  AlertCircle,
  XCircle,
  Sparkles,
  ShieldAlert,
  Loader2,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import {
  fetchCandidateBuyScore,
  type BuyScoreResultData,
} from "@/lib/api";

export const AXIS_META: Record<
  string,
  { label: string; description: string; iconColor: string }
> = {
  versatility: {
    label: "Versatility",
    description: "How easily this item pairs into complete outfits",
    iconColor: "text-blue-500",
  },
  redundancy: {
    label: "Uniqueness",
    description: "How distinct this is from garments you already own",
    iconColor: "text-purple-500",
  },
  seasonal_relevance: {
    label: "Timing",
    description: "How close right now is to this item being useful",
    iconColor: "text-amber-500",
  },
  budget_impact: {
    label: "Value for Money",
    description: "Cost-per-wear efficiency & low return risk",
    iconColor: "text-emerald-500",
  },
  style_alignment: {
    label: "Style Fit",
    description: "Alignment with your established personal style",
    iconColor: "text-indigo-500",
  },
  occasion_coverage: {
    label: "Wardrobe Gap",
    description: "Whether this fills a missing occasion in your wardrobe",
    iconColor: "text-rose-500",
  },
};

const VERDICT_CONFIG = {
  buy: {
    label: "BUY",
    badgeClass: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
    bgGradient: "from-emerald-500/10 via-emerald-500/5 to-transparent",
    chartColor: "#10b981",
    icon: CheckCircle2,
    accentBorder: "border-emerald-500/30",
    tagline: "High confidence addition to your wardrobe.",
  },
  consider: {
    label: "CONSIDER",
    badgeClass: "bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30",
    bgGradient: "from-amber-500/10 via-amber-500/5 to-transparent",
    chartColor: "#f59e0b",
    icon: AlertCircle,
    accentBorder: "border-amber-500/30",
    tagline: "Solid piece with a few trade-offs to keep in mind.",
  },
  skip: {
    label: "SKIP",
    badgeClass: "bg-rose-500/15 text-rose-700 dark:text-rose-300 border-rose-500/30",
    bgGradient: "from-rose-500/10 via-rose-500/5 to-transparent",
    chartColor: "#f43f5e",
    icon: XCircle,
    accentBorder: "border-rose-500/30",
    tagline: "Redundant or poor value — consider skipping.",
  },
};

interface VerdictCardProps {
  candidateId?: number;
  initialData?: BuyScoreResultData | null;
  className?: string;
}

export function VerdictCard({ candidateId, initialData, className = "" }: VerdictCardProps) {
  const [data, setData] = useState<BuyScoreResultData | null>(initialData || null);
  const [loading, setLoading] = useState<boolean>(!initialData && Boolean(candidateId));
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    if (initialData) {
      setData(initialData);
      return;
    }
    if (!candidateId) return;

    let isMounted = true;
    setLoading(true);
    setError(null);

    fetchCandidateBuyScore(candidateId)
      .then((res) => {
        if (isMounted) setData(res);
      })
      .catch((err) => {
        if (isMounted) setError(err instanceof Error ? err.message : "Failed to load verdict");
      })
      .finally(() => {
        if (isMounted) setLoading(false);
      });

    return () => {
      isMounted = false;
    };
  }, [candidateId, initialData]);

  if (loading) {
    return (
      <Card className={`border-primary/20 shadow-md ${className}`}>
        <CardContent className="py-12 flex flex-col items-center justify-center gap-3">
          <Loader2 className="h-8 w-8 animate-spin text-primary" />
          <p className="text-sm font-medium text-muted-foreground">
            Synthesizing 6 decision axes into verdict...
          </p>
        </CardContent>
      </Card>
    );
  }

  if (error || !data) {
    return (
      <Card className={`border-destructive/30 bg-destructive/5 ${className}`}>
        <CardContent className="py-8 text-center space-y-2">
          <ShieldAlert className="h-8 w-8 text-destructive mx-auto" />
          <p className="text-sm font-medium text-destructive">
            {error || "No verdict data available"}
          </p>
        </CardContent>
      </Card>
    );
  }

  const verdictKey = (data.verdict.toLowerCase() as keyof typeof VERDICT_CONFIG) in VERDICT_CONFIG
    ? (data.verdict.toLowerCase() as keyof typeof VERDICT_CONFIG)
    : "consider";

  const config = VERDICT_CONFIG[verdictKey];
  const VerdictIcon = config.icon;

  const radarData = (data.axes || []).map((axisItem) => {
    const meta = AXIS_META[axisItem.axis] || { label: axisItem.axis };
    return {
      axisKey: axisItem.axis,
      axisLabel: meta.label,
      score: axisItem.score,
      fullMark: 100,
    };
  });

  return (
    <motion.div
      initial={{ opacity: 0, y: 16 }}
      animate={{ opacity: 1, y: 0 }}
      transition={{ duration: 0.4, ease: "easeOut" }}
      className={className}
    >
      <Card className={`overflow-hidden shadow-lg border-2 ${config.accentBorder}`}>
        <div className={`p-6 bg-gradient-to-br ${config.bgGradient} border-b`}>
          <div className="flex flex-col md:flex-row items-start md:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div
                className={`flex items-center justify-center h-16 w-16 rounded-2xl border-2 shadow-sm ${config.badgeClass}`}
              >
                <VerdictIcon className="h-9 w-9" />
              </div>

              <div>
                <div className="flex items-center gap-2.5">
                  <span className="text-2xl sm:text-3xl font-extrabold tracking-tight">
                    {config.label}
                  </span>
                  <Badge variant="outline" className={`px-2.5 py-0.5 font-bold text-sm ${config.badgeClass}`}>
                    Score: {data.overall_score.toFixed(1)} / 100
                  </Badge>
                </div>
                <p className="text-xs text-muted-foreground mt-0.5">{config.tagline}</p>
              </div>
            </div>

            <div className="w-full md:w-auto md:text-right bg-background/80 backdrop-blur-sm px-4 py-2 rounded-xl border">
              <div className="text-xs font-semibold text-muted-foreground uppercase tracking-wider">
                Overall Buy Score
              </div>
              <div className="text-2xl font-black" style={{ color: config.chartColor }}>
                {Math.round(data.overall_score)}
                <span className="text-xs text-muted-foreground font-normal"> / 100</span>
              </div>
            </div>
          </div>

          <div className="mt-4 p-3.5 bg-background/90 backdrop-blur-md rounded-xl border border-border shadow-sm flex items-start gap-3">
            <Sparkles className="h-5 w-5 text-primary shrink-0 mt-0.5" />
            <div>
              <div className="text-xs font-bold text-primary uppercase tracking-wider">
                The Verdict Headline
              </div>
              <p className="text-sm font-semibold text-foreground mt-0.5 leading-relaxed">
                {data.headline_reason}
              </p>
            </div>
          </div>
        </div>

        <CardContent className="p-6">
          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-center">
            <div className="lg:col-span-5 flex flex-col items-center justify-center p-2 rounded-2xl bg-muted/20 border">
              <div className="w-full text-center pb-1">
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  6-Axis Decision Profile
                </span>
              </div>

              <div className="w-full h-[280px] sm:h-[320px]">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" outerRadius="70%" data={radarData}>
                    <PolarGrid stroke="#94a3b8" strokeOpacity={0.25} />
                    <PolarAngleAxis
                      dataKey="axisLabel"
                      tick={{ fill: "currentColor", fontSize: 11, fontWeight: 600 }}
                      className="text-foreground fill-foreground"
                    />
                    <PolarRadiusAxis
                      angle={30}
                      domain={[0, 100]}
                      tick={{ fontSize: 9, fill: "#94a3b8" }}
                      axisLine={false}
                    />
                    <Radar
                      name="Axis Score"
                      dataKey="score"
                      stroke={config.chartColor}
                      fill={config.chartColor}
                      fillOpacity={0.35}
                      strokeWidth={2}
                    />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const item = payload[0].payload;
                          return (
                            <div className="bg-popover text-popover-foreground px-3 py-2 rounded-lg shadow-md border text-xs">
                              <p className="font-bold">{item.axisLabel}</p>
                              <p className="text-primary font-semibold">
                                Score: {item.score} / 100
                              </p>
                            </div>
                          );
                        }
                        return null;
                      }}
                    />
                  </RadarChart>
                </ResponsiveContainer>
              </div>

              <p className="text-[11px] text-muted-foreground text-center px-4 pt-1">
                A larger polygon indicates stronger alignment across versatility, timing, style, and economics.
              </p>
            </div>

            <div className="lg:col-span-7 space-y-3">
              <div className="flex items-center justify-between pb-1 border-b">
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Decision Breakdown & Evidence
                </span>
                <span className="text-xs text-muted-foreground">0–100 Favorable Scale</span>
              </div>

              <div className="space-y-2.5">
                {data.axes.map((axisItem, idx) => {
                  const meta = AXIS_META[axisItem.axis] || {
                    label: axisItem.axis,
                    description: "",
                    iconColor: "text-primary",
                  };

                  const isHigh = axisItem.score >= 70;
                  const isMedium = axisItem.score >= 45 && axisItem.score < 70;

                  return (
                    <motion.div
                      key={axisItem.axis}
                      initial={{ opacity: 0, x: 8 }}
                      animate={{ opacity: 1, x: 0 }}
                      transition={{ delay: idx * 0.05 + 0.1 }}
                      className="p-3 rounded-xl border bg-card hover:bg-muted/30 transition-colors"
                    >
                      <div className="flex items-center justify-between gap-2 mb-1.5">
                        <div className="flex items-center gap-2">
                          <span className="font-bold text-sm text-foreground">
                            {meta.label}
                          </span>
                          <span className="text-[11px] text-muted-foreground hidden sm:inline">
                            • {meta.description}
                          </span>
                        </div>

                        <div className="flex items-center gap-1.5 shrink-0">
                          <span
                            className={`text-xs font-bold px-2 py-0.5 rounded-md ${
                              isHigh
                                ? "bg-emerald-500/10 text-emerald-600 dark:text-emerald-400"
                                : isMedium
                                ? "bg-amber-500/10 text-amber-600 dark:text-amber-400"
                                : "bg-rose-500/10 text-rose-600 dark:text-rose-400"
                            }`}
                          >
                            {Math.round(axisItem.score)}
                          </span>
                        </div>
                      </div>

                      <Progress
                        value={axisItem.score}
                        className="h-1.5 mb-2 bg-muted"
                      />

                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {axisItem.reason}
                      </p>
                    </motion.div>
                  );
                })}
              </div>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
