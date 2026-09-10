"use client";

import React from "react";
import { motion } from "framer-motion";
import {
  Sparkles,
  ArrowRight,
  CheckCircle2,
  Shirt,
  TrendingUp,
  Layers,
  Scale,
  Zap,
} from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { DecisionSummaryPanel } from "@/components/DecisionSummaryPanel";
import { fadeUpVariants } from "@/lib/animations";
import type {
  OpportunityCostCompareResponseData,
  CandidateItemData,
  DecisionSummaryMetricsData,
} from "@/lib/api";

interface OpportunityCostCardProps {
  data: OpportunityCostCompareResponseData;
  candidateItemMap?: Record<number, CandidateItemData>;
  className?: string;
}

export function OpportunityCostCard({
  data,
  candidateItemMap = {},
  className = "",
}: OpportunityCostCardProps) {
  const {
    candidate,
    alternative_bundle,
    candidate_versatility,
    alternative_bundle_versatility,
    versatility_delta,
    candidate_outfit_count,
    alternative_bundle_outfit_count,
    outfit_count_delta,
    candidate_name,
    alternative_names,
  } = data;

  const isBundleFavorable = alternative_bundle.overall_score >= candidate.overall_score;
  const isVersatilityGain = outfit_count_delta > 0;

  const candidateItem = candidateItemMap[candidate.candidate_id];
  const altItems = alternative_bundle.item_ids.map((id) => candidateItemMap[id]);

  const candidateSummaryMetrics: DecisionSummaryMetricsData =
    candidate.summary_panel ||
    (() => {
      const redAxis = candidate.axes?.find((a) => a.axis === "redundancy");
      const seasAxis = candidate.axes?.find((a) => a.axis === "seasonal_relevance");
      const versAxis = candidate.axes?.find((a) => a.axis === "versatility");
      const dupSim = redAxis ? Math.max(0, 100 - redAxis.score) : 0;
      const price = candidateItem?.price ?? 120;
      return {
        versatility: candidate_versatility ?? versAxis?.score ?? 50,
        versatility_outfits_count:
          candidate_outfit_count ??
          (typeof versAxis?.raw_evidence?.combinations_count === "number"
            ? versAxis.raw_evidence.combinations_count
            : 0),
        duplicate_risk: dupSim,
        duplicate_risk_label: `${dupSim.toFixed(1)}% similarity to wardrobe`,
        seasonality: seasAxis?.score ?? 70,
        seasonality_label: (seasAxis?.score ?? 70) >= 80 ? "In-Season (High utility)" : "Upcoming",
        cost_per_wear: price / 30,
        cost_per_wear_formatted: `$${(price / 30).toFixed(2)} / wear`,
        sustainability_tier: candidateItem?.attributes?.material ? "Lower impact" : "Unrated",
        sustainability_reason: "Rough estimate based on item material. Not a certified rating.",
        is_estimate: true,
      };
    })();

  const bundleSummaryMetrics: DecisionSummaryMetricsData =
    alternative_bundle.summary_panel ||
    (() => {
      const redAxis = alternative_bundle.axes?.find((a) => a.axis === "redundancy");
      const seasAxis = alternative_bundle.axes?.find((a) => a.axis === "seasonal_relevance");
      const versAxis = alternative_bundle.axes?.find((a) => a.axis === "versatility");
      const dupSim = redAxis ? Math.max(0, 100 - redAxis.score) : 0;
      const totalPrice = alternative_bundle.total_price || 150;
      return {
        versatility: alternative_bundle_versatility ?? versAxis?.score ?? 75,
        versatility_outfits_count:
          alternative_bundle_outfit_count ??
          (typeof versAxis?.raw_evidence?.total_outfits_count === "number"
            ? versAxis.raw_evidence.total_outfits_count
            : 0),
        duplicate_risk: dupSim,
        duplicate_risk_label: `${dupSim.toFixed(1)}% similarity to wardrobe`,
        seasonality: seasAxis?.score ?? 85,
        seasonality_label: (seasAxis?.score ?? 85) >= 80 ? "In-Season (High utility)" : "Upcoming",
        cost_per_wear: totalPrice / 50,
        cost_per_wear_formatted: `$${(totalPrice / 50).toFixed(2)} / wear`,
        sustainability_tier: "Lower impact",
        sustainability_reason: "Rough estimate based on bundle materials. Not a certified rating.",
        is_estimate: true,
      };
    })();

  const candidateBadgeVariant: "buy" | "consider" | "skip" =
    candidate.verdict === "buy" ? "buy" : candidate.verdict === "consider" ? "consider" : "skip";

  return (
    <motion.div
      initial="hidden"
      animate="visible"
      variants={fadeUpVariants}
      className={`space-y-6 ${className}`}
    >
      {/* 1. HERO HEADLINE CARD */}
      <Card className="rounded-2xl border-2 border-primary/30 bg-gradient-to-br from-primary/10 via-primary/5 to-card shadow-xl overflow-hidden">
        <CardContent className="p-6 sm:p-8 space-y-6">
          <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider">
            <Scale className="h-4 w-4 text-primary" />
            <span>Opportunity Cost Verdict</span>
          </div>

          {/* EXACT TEMPLATE COPY REQUIRED BY MILESTONE 28 */}
          <div className="space-y-2">
            <h2 className="text-xl sm:text-2xl lg:text-3xl font-black tracking-tight text-foreground leading-tight">
              Instead of{" "}
              <span className="text-primary underline decoration-primary/40 underline-offset-4">
                {candidate_name}
              </span>
              , these two items would create{" "}
              <span className="text-emerald-600 dark:text-emerald-400 font-extrabold px-2 py-0.5 rounded-xl bg-emerald-500/15 border border-emerald-500/30 inline-block">
                {alternative_bundle_outfit_count}
              </span>{" "}
              new outfit combinations.
            </h2>
            <p className="text-sm sm:text-base text-muted-foreground pt-1">
              {isVersatilityGain ? (
                <>
                  That’s{" "}
                  <span className="font-bold text-emerald-600 dark:text-emerald-400">
                    +{outfit_count_delta} additional outfit{outfit_count_delta > 1 ? "s" : ""}
                  </span>{" "}
                  ({candidate_outfit_count} vs {alternative_bundle_outfit_count}) unlocked by choosing the alternative bundle.
                </>
              ) : (
                <>
                  Comparison between 1 standalone item ({candidate_outfit_count} outfit{candidate_outfit_count > 1 ? "s" : ""}) and the 2-item alternative bundle ({alternative_bundle_outfit_count} outfit{alternative_bundle_outfit_count > 1 ? "s" : ""}).
                </>
              )}
            </p>
          </div>

          {/* Versatility & Score Delta Badges */}
          <div className="flex flex-wrap items-center gap-3 pt-2">
            <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-background border shadow-sm text-xs font-bold">
              <Zap className="h-4 w-4 text-amber-500" />
              <span>Versatility Delta:</span>
              <span
                className={`font-mono text-sm ${
                  versatility_delta >= 0
                    ? "text-emerald-600 dark:text-emerald-400"
                    : "text-rose-600 dark:text-rose-400"
                }`}
              >
                {versatility_delta >= 0 ? `+${versatility_delta.toFixed(1)}` : versatility_delta.toFixed(1)} pts
              </span>
            </div>

            <div className="flex items-center gap-2 px-3.5 py-1.5 rounded-xl bg-background border shadow-sm text-xs font-bold">
              <TrendingUp className="h-4 w-4 text-emerald-500" />
              <span>Score Comparison:</span>
              <span className="font-mono text-sm text-foreground">
                {candidate.overall_score.toFixed(1)} vs {alternative_bundle.overall_score.toFixed(1)}
              </span>
            </div>
          </div>
        </CardContent>
      </Card>

      {/* 2. SIDE-BY-SIDE VISUAL COMPARISON GRID */}
      <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-stretch">
        {/* LEFT COLUMN: CANDIDATE ITEM */}
        <Card className="lg:col-span-5 flex flex-col justify-between rounded-2xl border shadow-md bg-card p-6 space-y-6">
          <div>
            <div className="flex items-center justify-between pb-3 border-b mb-4">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Option A • Original Candidate
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Badge
                  variant={candidateBadgeVariant}
                  className="font-bold text-xs capitalize"
                >
                  {candidate.verdict}
                </Badge>
                <ConfidenceBadge confidence={candidate.confidence} size="sm" />
              </div>
            </div>

            {/* Candidate Thumbnail / Graphic */}
            <div className="flex items-center gap-4 mb-4">
              {candidateItem?.cloudinary_url ? (
                <img
                  src={candidateItem.cloudinary_url}
                  alt={candidate_name}
                  className="h-20 w-20 rounded-2xl object-cover border-2 shadow-sm"
                />
              ) : (
                <div className="flex h-20 w-20 shrink-0 items-center justify-center rounded-2xl bg-primary/10 border-2 border-primary/20 text-primary shadow-sm">
                  <Shirt className="h-9 w-9" />
                </div>
              )}
              <div>
                <h3 className="text-lg font-black text-foreground">{candidate_name}</h3>
                <p className="text-xs text-muted-foreground mt-0.5">
                  ID <code className="font-mono font-bold text-primary">#{candidate.candidate_id}</code>
                </p>
                {candidateItem?.price && (
                  <p className="text-sm font-extrabold text-foreground mt-1">
                    ${candidateItem.price.toFixed(2)}
                  </p>
                )}
              </div>
            </div>

            <p className="text-xs text-muted-foreground leading-relaxed bg-muted/30 p-3 rounded-xl border">
              {candidate.headline_reason}
            </p>
          </div>

          <div className="space-y-3 pt-3 border-t">
            <div className="flex items-center justify-between text-xs font-bold">
              <span className="text-muted-foreground">Candidate Buy Score</span>
              <span className="font-mono text-base font-black text-primary">
                {candidate.overall_score.toFixed(1)} / 100
              </span>
            </div>
            <Progress value={candidate.overall_score} className="h-2" />

            <div className="flex items-center justify-between text-xs pt-1">
              <span className="text-muted-foreground font-medium">Outfits Enabled:</span>
              <span className="font-bold text-foreground font-mono">
                {candidate_outfit_count} combination{candidate_outfit_count !== 1 ? "s" : ""}
              </span>
            </div>

            {/* Milestone 31: 5-Metric Decision Summary Panel */}
            <div className="pt-4 border-t">
              <DecisionSummaryPanel
                metrics={candidateSummaryMetrics}
                variant="compact"
                columns={2}
                title="Candidate 5-Metric Profile"
              />
            </div>
          </div>
        </Card>

        {/* MIDDLE ICON SEPARATOR */}
        <div className="lg:col-span-2 flex flex-row lg:flex-col items-center justify-center gap-2 py-2 lg:py-0">
          <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-muted/80 border text-muted-foreground font-black shadow-sm">
            VS
          </div>
        </div>

        {/* RIGHT COLUMN: ALTERNATIVE BUNDLE */}
        <Card className="lg:col-span-5 flex flex-col justify-between rounded-2xl border-2 border-emerald-500/40 shadow-md bg-gradient-to-br from-emerald-500/5 to-card p-6 space-y-6">
          <div>
            <div className="flex items-center justify-between pb-3 border-b border-emerald-500/20 mb-4">
              <div className="flex items-center gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-emerald-700 dark:text-emerald-300">
                  Option B • 2-Item Alternative Bundle
                </span>
              </div>
              <div className="flex items-center gap-2">
                <Badge variant="buy" className="font-black text-xs px-2.5 py-0.5">
                  {alternative_bundle.verdict.toUpperCase()}
                </Badge>
                <ConfidenceBadge confidence={alternative_bundle.confidence} size="sm" />
              </div>
            </div>

            {/* 2 Alternative Thumbnails / Chips */}
            <div className="grid grid-cols-2 gap-3 mb-4">
              {alternative_bundle.item_ids.map((id, idx) => {
                const aItem = altItems[idx];
                const aName = alternative_names[idx] || `Item #${id}`;
                return (
                  <div
                    key={id}
                    className="flex flex-col items-center text-center p-3 rounded-xl border bg-card shadow-sm space-y-2"
                  >
                    {aItem?.cloudinary_url ? (
                      <img
                        src={aItem.cloudinary_url}
                        alt={aName}
                        className="h-14 w-14 rounded-xl object-cover border"
                      />
                    ) : (
                      <div className="flex h-14 w-14 items-center justify-center rounded-xl bg-emerald-500/10 border border-emerald-500/20 text-emerald-600">
                        <Shirt className="h-7 w-7" />
                      </div>
                    )}
                    <div className="min-w-0 w-full">
                      <p className="text-xs font-bold text-foreground truncate">{aName}</p>
                      <p className="text-[10px] text-muted-foreground font-mono">#{id}</p>
                    </div>
                  </div>
                );
              })}
            </div>

            <p className="text-xs text-muted-foreground leading-relaxed bg-background p-3 rounded-xl border">
              {alternative_bundle.headline_reason}
            </p>
          </div>

          <div className="space-y-3 pt-3 border-t border-emerald-500/20">
            <div className="flex items-center justify-between text-xs font-bold">
              <span className="text-muted-foreground">Bundle Overall Score</span>
              <span className="font-mono text-base font-black text-emerald-600 dark:text-emerald-400">
                {alternative_bundle.overall_score.toFixed(1)} / 100
              </span>
            </div>
            <Progress
              value={alternative_bundle.overall_score}
              className="h-2"
              indicatorClassName="bg-emerald-500"
            />

            <div className="flex items-center justify-between text-xs pt-1">
              <span className="text-muted-foreground font-medium">Outfits Enabled:</span>
              <span className="font-bold text-emerald-600 dark:text-emerald-400 font-mono">
                {alternative_bundle_outfit_count} combinations ({outfit_count_delta >= 0 ? `+${outfit_count_delta}` : outfit_count_delta})
              </span>
            </div>

            {/* Milestone 31: 5-Metric Decision Summary Panel */}
            <div className="pt-4 border-t border-emerald-500/20">
              <DecisionSummaryPanel
                metrics={bundleSummaryMetrics}
                variant="compact"
                columns={2}
                title="Bundle 5-Metric Profile"
              />
            </div>
          </div>
        </Card>
      </div>
    </motion.div>
  );
}
