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
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { DecisionSummaryPanel } from "@/components/DecisionSummaryPanel";
import {
  fetchCandidateBuyScore,
  type BuyScoreResultData,
  type DecisionSummaryMetricsData,
} from "@/lib/api";

import {
  fadeUpVariants,
  staggerContainerVariants,
  staggerItemVariants,
} from "@/lib/animations";

export const AXIS_META: Record<
  string,
  { label: string; description: string; iconColor: string }
> = {
  versatility: {
    label: "Versatility",
    description: "How easily this item pairs into complete outfits with your current wardrobe",
    iconColor: "text-blue-500",
  },
  redundancy: {
    label: "Uniqueness",
    description: "Wardrobe distinctness (higher is better; 100 minus duplicate risk %)",
    iconColor: "text-purple-500",
  },
  seasonal_relevance: {
    label: "Timing",
    description: "Seasonal readiness — how immediately wearable this item is right now",
    iconColor: "text-amber-500",
  },
  budget_impact: {
    label: "Value for Money",
    description: "Cost-per-wear efficiency and low return risk based on expected wears",
    iconColor: "text-emerald-500",
  },
  style_alignment: {
    label: "Style Fit",
    description: "Alignment with your established personal wardrobe style",
    iconColor: "text-indigo-500",
  },
  occasion_coverage: {
    label: "Wardrobe Gap",
    description: "Whether this item fills a missing occasion or expands your closet",
    iconColor: "text-rose-500",
  },
};

const VERDICT_CONFIG: Record<
  string,
  {
    label: string;
    badgeVariant: "buy" | "consider" | "skip";
    badgeClass: string;
    bgGradient: string;
    chartColor: string;
    gradientId: string;
    icon: any;
    accentBorder: string;
    tagline: string;
  }
> = {
  buy: {
    label: "BUY",
    badgeVariant: "buy",
    badgeClass: "bg-emerald-500/15 text-emerald-700 dark:text-emerald-300 border-emerald-500/30",
    bgGradient: "from-emerald-500/10 via-emerald-500/5 to-transparent",
    chartColor: "#10b981",
    gradientId: "radarGradient-buy",
    icon: CheckCircle2,
    accentBorder: "border-emerald-500/30",
    tagline: "High confidence addition to your wardrobe.",
  },
  consider: {
    label: "CONSIDER",
    badgeVariant: "consider",
    badgeClass: "bg-amber-500/15 text-amber-700 dark:text-amber-300 border-amber-500/30",
    bgGradient: "from-amber-500/10 via-amber-500/5 to-transparent",
    chartColor: "#f59e0b",
    gradientId: "radarGradient-consider",
    icon: AlertCircle,
    accentBorder: "border-amber-500/30",
    tagline: "Solid piece with a few trade-offs to keep in mind.",
  },
  skip: {
    label: "SKIP",
    badgeVariant: "skip",
    badgeClass: "bg-rose-500/15 text-rose-700 dark:text-rose-300 border-rose-500/30",
    bgGradient: "from-rose-500/10 via-rose-500/5 to-transparent",
    chartColor: "#f43f5e",
    gradientId: "radarGradient-skip",
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
  const [isMobile, setIsMobile] = useState<boolean>(false);

  useEffect(() => {
    const handleResize = () => setIsMobile(window.innerWidth < 640);
    handleResize();
    window.addEventListener("resize", handleResize);
    return () => window.removeEventListener("resize", handleResize);
  }, []);

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

  const redundancyAxis = data.axes.find((a) => a.axis === "redundancy");
  const seasonalityAxis = data.axes.find((a) => a.axis === "seasonal_relevance");
  const versatilityAxis = data.axes.find((a) => a.axis === "versatility");
  const fallbackDupRisk = redundancyAxis ? Math.max(0, 100 - redundancyAxis.score) : 0;

  const summaryMetrics: DecisionSummaryMetricsData = data.summary_panel || {
    versatility: versatilityAxis ? versatilityAxis.score : 50,
    versatility_outfits_count:
      typeof versatilityAxis?.raw_evidence?.combinations_count === "number"
        ? versatilityAxis.raw_evidence.combinations_count
        : 0,
    duplicate_risk: fallbackDupRisk,
    duplicate_risk_label: `${fallbackDupRisk.toFixed(1)}% similarity to closet`,
    seasonality: seasonalityAxis ? seasonalityAxis.score : 50,
    seasonality_label: (seasonalityAxis?.score || 50) >= 80 ? "In-Season (High utility)" : "Upcoming",
    cost_per_wear: 3.5,
    cost_per_wear_formatted: "$3.50 / wear",
    sustainability_tier: "Lower impact",
    sustainability_reason: "Rough estimate based on natural fibers (cotton). Not a certified rating.",
    is_estimate: true,
  };

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={fadeUpVariants}
      className={className}
    >
      <Card className={`overflow-hidden rounded-2xl shadow-xl border-2 ${config.accentBorder} bg-card`}>
        <div className={`p-6 sm:p-8 bg-gradient-to-br ${config.bgGradient} border-b`}>
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4">
            <div className="flex items-center gap-4">
              <div
                className={`flex items-center justify-center h-16 w-16 sm:h-20 sm:w-20 rounded-2xl border-2 shadow-sm ${config.badgeClass}`}
              >
                <VerdictIcon className="h-10 w-10 sm:h-12 sm:w-12" />
              </div>

              <div>
                <div className="flex flex-wrap items-center gap-2.5 sm:gap-3">
                  <span className="text-3xl sm:text-4xl font-black tracking-tight">
                    {config.label}
                  </span>
                  <Badge variant={config.badgeVariant} className="px-3 py-1 font-bold text-sm sm:text-base">
                    Score: {data.overall_score.toFixed(1)} / 100
                  </Badge>
                  <ConfidenceBadge confidence={data.confidence} size="md" />
                </div>
                <p className="text-xs sm:text-sm text-muted-foreground mt-1">{config.tagline}</p>
              </div>
            </div>

            <div className="w-full sm:w-auto text-left sm:text-right bg-background/90 backdrop-blur-md px-5 py-3 rounded-2xl border shadow-sm">
              <div className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
                Overall Buy Score
              </div>
              <div className="text-3xl sm:text-4xl font-black tracking-tight" style={{ color: config.chartColor }}>
                {Math.round(data.overall_score)}
                <span className="text-sm font-semibold text-muted-foreground"> / 100</span>
              </div>
            </div>
          </div>

          <div className="mt-5 p-4 bg-background/95 backdrop-blur-md rounded-2xl border shadow-sm flex items-start gap-3.5">
            <div className="p-2 rounded-xl bg-primary/10 text-primary shrink-0 mt-0.5">
              <Sparkles className="h-5 w-5" />
            </div>
            <div className="flex-1">
              <div className="text-[11px] font-bold text-primary uppercase tracking-wider">
                The Verdict Headline
              </div>
              <p className="text-sm sm:text-base font-semibold text-foreground mt-0.5 leading-relaxed">
                {data.headline_reason}
              </p>
            </div>
          </div>
        </div>

        <CardContent className="p-6 sm:p-8 space-y-8">
          {/* Milestone 31: 5-Metric Summary Panel */}
          <div className="pb-6 border-b">
            <DecisionSummaryPanel metrics={summaryMetrics} />
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 lg:gap-10 items-stretch">
            <div className="lg:col-span-5 flex flex-col items-center justify-between p-5 rounded-2xl bg-muted/20 border">
              <div className="w-full text-center pb-2 border-b border-border/60">
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  6-Axis Decision Profile
                </span>
              </div>

              <div className="w-full h-[270px] sm:h-[340px] my-2">
                <ResponsiveContainer width="100%" height="100%">
                  <RadarChart cx="50%" cy="50%" outerRadius={isMobile ? "52%" : "68%"} data={radarData}>
                    <defs>
                      <linearGradient id="radarGradient-buy" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#10b981" stopOpacity={0.65} />
                        <stop offset="100%" stopColor="#059669" stopOpacity={0.2} />
                      </linearGradient>
                      <linearGradient id="radarGradient-consider" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#f59e0b" stopOpacity={0.65} />
                        <stop offset="100%" stopColor="#d97706" stopOpacity={0.2} />
                      </linearGradient>
                      <linearGradient id="radarGradient-skip" x1="0" y1="0" x2="0" y2="1">
                        <stop offset="0%" stopColor="#f43f5e" stopOpacity={0.65} />
                        <stop offset="100%" stopColor="#e11d48" stopOpacity={0.2} />
                      </linearGradient>
                    </defs>
                    <PolarGrid stroke="#cbd5e1" strokeOpacity={0.6} />
                    <PolarAngleAxis
                      dataKey="axisLabel"
                      tick={{ fill: "#334155", fontSize: isMobile ? 9 : 11, fontWeight: 700 }}
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
                      fill={`url(#${config.gradientId})`}
                      fillOpacity={1}
                      strokeWidth={2.5}
                      dot={{ r: 4, fill: config.chartColor, stroke: "#ffffff", strokeWidth: 2 }}
                    />
                    <Tooltip
                      content={({ active, payload }) => {
                        if (active && payload && payload.length) {
                          const item = payload[0].payload;
                          return (
                            <div className="bg-popover text-popover-foreground px-3 py-2 rounded-xl shadow-lg border text-xs">
                              <p className="font-bold">{item.axisLabel}</p>
                              <p className="font-extrabold text-sm" style={{ color: config.chartColor }}>
                                Score: {Math.round(item.score)} / 100
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

              <p className="text-[11px] text-muted-foreground text-center px-2 pt-2 border-t border-border/60">
                A larger polygon indicates stronger overall alignment across versatility, timing, style, and economics. Note: Uniqueness is scored 0–100 (where 100 = completely unique, 0% duplicate overlap with closet).
              </p>
            </div>

            <div className="lg:col-span-7 flex flex-col justify-between space-y-4">
              <div className="flex items-center justify-between pb-2 border-b">
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Decision Breakdown & Evidence
                </span>
                <span className="text-xs font-medium text-muted-foreground">0–100 Favorable Scale</span>
              </div>

              <motion.div
                initial="hidden"
                animate="visible"
                variants={staggerContainerVariants}
                className="space-y-3 flex-1 flex flex-col justify-between"
              >
                {data.axes.map((axisItem) => {
                  const meta = AXIS_META[axisItem.axis] || {
                    label: axisItem.axis,
                    description: "",
                    iconColor: "text-primary",
                  };

                  const isHigh = axisItem.score >= 70;
                  const isMedium = axisItem.score >= 45 && axisItem.score < 70;

                  const indicatorClass = isHigh
                    ? "bg-emerald-500"
                    : isMedium
                    ? "bg-amber-500"
                    : "bg-rose-500";

                  return (
                    <motion.div
                      key={axisItem.axis}
                      variants={staggerItemVariants}
                      className="p-3.5 rounded-xl border bg-card hover:bg-muted/20 transition-colors shadow-xs"
                    >
                      <div className="flex items-center justify-between gap-2 mb-2">
                        <div className="flex items-center gap-2 min-w-0">
                          <span className="font-bold text-sm text-foreground shrink-0">
                            {meta.label}
                          </span>
                          <span className="text-xs text-muted-foreground hidden sm:inline truncate">
                            • {meta.description}
                          </span>
                        </div>

                        <div className="flex items-center gap-1.5 shrink-0">
                          <Badge
                            variant={isHigh ? "buy" : isMedium ? "consider" : "skip"}
                            className="text-xs font-extrabold px-2 py-0.5"
                          >
                            {Math.round(axisItem.score)}
                          </Badge>
                        </div>
                      </div>

                      <Progress
                        value={axisItem.score}
                        className="h-2 mb-2 bg-muted/60"
                        indicatorClassName={indicatorClass}
                      />

                      <p className="text-xs text-muted-foreground leading-relaxed font-normal">
                        {axisItem.reason}
                      </p>
                    </motion.div>
                  );
                })}
              </motion.div>
            </div>
          </div>
        </CardContent>
      </Card>
    </motion.div>
  );
}
