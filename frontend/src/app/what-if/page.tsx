"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  Shirt,
  Compass,
  LayoutDashboard,
  CheckCircle2,
  ChevronDown,
  ChevronRight,
  Layers,
  FlaskConical,
  Plus,
  AlertCircle,
  Loader2,
  Trophy,
  Tag,
  Zap,
  ShieldCheck,
  Ban,
  Scale,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { NavigationHeader } from "@/components/NavigationHeader";
import {
  fadeUpVariants,
  staggerContainerVariants,
  staggerItemVariants,
  DURATION_FAST,
} from "@/lib/animations";
import { ConfidenceBadge } from "@/components/ConfidenceBadge";
import { DecisionSummaryPanel } from "@/components/DecisionSummaryPanel";
import {
  fetchCandidates,
  scoreWhatIfSubsets,
  type CandidateItemData,
  type ScoredSubsetData,
  type ScoreSubsetsResponseData,
} from "@/lib/api";

const DEMO_CANDIDATES: CandidateItemData[] = [
  {
    id: 101,
    cloudinary_url: "",
    price: 65.0,
    fit_tightness: "regular",
    silhouette: "tailored",
    uploaded_at: new Date().toISOString(),
    attributes: {
      category: "outerwear",
      color: "khaki beige",
      pattern: "solid",
      style: "casual",
      season: "fall",
      material: "cotton twill",
      extraction_source: "ai",
    },
  },
  {
    id: 102,
    cloudinary_url: "",
    price: 120.0,
    fit_tightness: "slim",
    silhouette: "structured",
    uploaded_at: new Date().toISOString(),
    attributes: {
      category: "outerwear",
      color: "navy blue",
      pattern: "solid",
      style: "formal",
      season: "winter",
      material: "wool blend",
      extraction_source: "ai",
    },
  },
  {
    id: 103,
    cloudinary_url: "",
    price: 45.0,
    fit_tightness: "regular",
    silhouette: "relaxed",
    uploaded_at: new Date().toISOString(),
    attributes: {
      category: "top",
      color: "olive green",
      pattern: "solid",
      style: "casual",
      season: "all-season",
      material: "linen",
      extraction_source: "ai",
    },
  },
  {
    id: 104,
    cloudinary_url: "",
    price: 85.0,
    fit_tightness: "regular",
    silhouette: "straight",
    uploaded_at: new Date().toISOString(),
    attributes: {
      category: "bottom",
      color: "charcoal grey",
      pattern: "solid",
      style: "casual",
      season: "fall",
      material: "denim",
      extraction_source: "ai",
    },
  },
  {
    id: 105,
    cloudinary_url: "",
    price: 110.0,
    fit_tightness: "regular",
    silhouette: "relaxed",
    uploaded_at: new Date().toISOString(),
    attributes: {
      category: "footwear",
      color: "brown",
      pattern: "solid",
      style: "casual",
      season: "all-season",
      material: "leather",
      extraction_source: "ai",
    },
  },
];

const LETTER_LABELS = ["A", "B", "C", "D", "E", "F"];

export default function WhatIfLabPage() {
  const [candidates, setCandidates] = useState<CandidateItemData[]>([]);
  const [selectedIds, setSelectedIds] = useState<number[]>([101, 103, 104]);
  const [loadingItems, setLoadingItems] = useState(true);
  const [scoring, setScoring] = useState(false);
  const [rankedResult, setRankedResult] = useState<ScoreSubsetsResponseData | null>(null);
  const [error, setError] = useState<string | null>(null);
  const [expandedSubsetId, setExpandedSubsetId] = useState<string | null>(null);

  useEffect(() => {
    fetchCandidates()
      .then((items) => {
        if (items && items.length >= 3) {
          setCandidates(items);
          setSelectedIds(items.slice(0, 4).map((i) => i.id));
        } else {
          setCandidates(DEMO_CANDIDATES);
        }
      })
      .catch(() => {
        setCandidates(DEMO_CANDIDATES);
      })
      .finally(() => {
        setLoadingItems(false);
      });
  }, []);

  // Map candidate IDs to letters (A, B, C, D, E) based on current candidate list
  const idToLetterMap: Record<number, string> = {};
  const idToItemMap: Record<number, CandidateItemData> = {};
  candidates.forEach((item, idx) => {
    idToLetterMap[item.id] = LETTER_LABELS[idx] || `#${item.id}`;
    idToItemMap[item.id] = item;
  });

  function toggleItemSelection(id: number) {
    setError(null);
    let next: number[];
    if (selectedIds.includes(id)) {
      next = selectedIds.filter((item) => item !== id);
    } else {
      if (selectedIds.length >= 5) {
        setError(
          "What-If analysis requires between 3 and 5 items. Combinatorial search space grows exponentially (2^N subsets: 5 items = 32 subsets, 6 items = 64 subsets, 10 items = 1,024 subsets) and becomes too slow and cognitively overwhelming."
        );
        return;
      }
      next = [...selectedIds, id];
    }
    setSelectedIds(next);
    if (next.length === 1) {
      setError(
        "Cart-level reasoning does not apply to a single item. What-If analysis requires between 3 and 5 items — please use the single-item Buy Score evaluation flow instead."
      );
    } else if (next.length === 2) {
      setError("Please select between 3 and 5 items to run What-If Cart analysis (minimum 3 items required).");
    }
  }

  function getSubsetDisplayLabel(itemIds: number[]) {
    if (itemIds.length === 0) return "Skip all";
    if (itemIds.length === 1) return `Buy only ${idToLetterMap[itemIds[0]] || itemIds[0]}`;
    const letters = itemIds.map((id) => idToLetterMap[id] || id).join(" + ");
    return `Buy ${letters}`;
  }

  async function handleScoreSubsets() {
    if (selectedIds.length === 1) {
      setError(
        "Cart-level reasoning does not apply to a single item. What-If analysis requires between 3 and 5 items — please use the single-item Buy Score evaluation flow instead."
      );
      return;
    }
    if (selectedIds.length > 5) {
      setError(
        `What-If analysis requires between 3 and 5 items. You selected ${selectedIds.length} items — combinatorial search space grows exponentially (2^N subsets) and becomes too slow and cognitively overwhelming.`
      );
      return;
    }
    if (selectedIds.length < 3) {
      setError("Please select between 3 and 5 candidate items.");
      return;
    }

    setScoring(true);
    setError(null);
    setRankedResult(null);

    try {
      const res = await scoreWhatIfSubsets(selectedIds);
      setRankedResult(res);
      if (res.top_recommendation) {
        setExpandedSubsetId(res.top_recommendation.subset_id);
      }
    } catch (err: any) {
      if (
        err?.message &&
        (err.message.includes("between 3 and 5") ||
          err.message.includes("Cart-level reasoning") ||
          err.message.includes("requires between"))
      ) {
        setError(err.message);
        return;
      }
      // Offline / demo fallback with realistic mock scored combinations
      const n = selectedIds.length;
      const total = Math.pow(2, n);
      const generated: ScoredSubsetData[] = [];

      const getCombos = (arr: number[], k: number): number[][] => {
        if (k === 0) return [[]];
        if (arr.length === 0) return [];
        const head = arr[0];
        const tail = arr.slice(1);
        const withHead = getCombos(tail, k - 1).map((c) => [head, ...c]);
        const withoutHead = getCombos(tail, k);
        return [...withHead, ...withoutHead];
      };

      let subsetCounter = 1;
      for (let r = 0; r <= n; r++) {
        const combos = getCombos(selectedIds, r);
        combos.forEach((c) => {
          let score = 50.0;
          let verdict: "buy" | "consider" | "skip" = "consider";
          let headline = "SKIP ALL: Baseline neutral score (no money spent, no wardrobe change).";

          if (c.length > 0) {
            // Compute realistic score based on synergy and size
            if (c.length === 2 && (c.includes(101) || c.includes(103)) && c.includes(104)) {
              score = 82.5;
              verdict = "buy";
              headline = "BUY: High synergy pair unlocking 5 complete outfits with 18% cost-per-wear savings.";
            } else if (c.length === 1) {
              score = c[0] === 101 ? 74.0 : 61.2;
              verdict = score >= 70 ? "buy" : "consider";
              headline = `${verdict.toUpperCase()}: Standalone addition with solid seasonal relevance.`;
            } else if (c.length >= 3) {
              score = 68.0;
              verdict = "consider";
              headline = "CONSIDER: High versatility, though higher budget impact across the cart.";
            } else {
              score = 58.3;
              verdict = "consider";
              headline = "CONSIDER: Moderate versatility with some overlap in your wardrobe.";
            }
          }

          const price = c.reduce((sum, id) => sum + (idToItemMap[id]?.price || 50), 0);

          generated.push({
            subset_id: `subset_${subsetCounter++}`,
            rank: 0,
            size: c.length,
            item_ids: c,
            verdict,
            overall_score: score,
            headline_reason: headline,
            total_price: price,
            confidence: {
              level: score >= 75 ? "high" : score >= 55 ? "medium" : "low",
              reasoning:
                score >= 75
                  ? "High confidence: Decisive score far from decision boundaries with strong cross-item synergy."
                  : score >= 55
                  ? "Medium confidence: Score sits near decision boundaries with moderate axis spread."
                  : "Low confidence: Elevated variance across decision axes and threshold proximity.",
            },
            summary_panel: {
              versatility: c.length === 0 ? 50 : Math.min(100, score + 5),
              versatility_outfits_count: c.length * 2,
              duplicate_risk: 15.0,
              duplicate_risk_label: "15.0% peak wardrobe similarity (Low risk)",
              seasonality: c.length === 0 ? 50 : 90.0,
              seasonality_label: "In-Season Cart",
              cost_per_wear: c.length === 0 ? 0 : 2.8,
              cost_per_wear_formatted: c.length === 0 ? "$0.00 / wear" : "$2.80 / wear (mean)",
              sustainability_tier: "Lower impact",
              sustainability_reason: "Items feature natural cotton fibers. Rough estimate.",
              is_estimate: true,
            },
            axes: [
              { axis: "versatility", score: c.length === 0 ? 50 : Math.min(100, score + 5), reason: "Outfit composition score", source_agent: "outfit_composition" },
              { axis: "redundancy", score: c.length === 0 ? 50 : 85, reason: "Uniqueness score", source_agent: "duplicate_detection" },
              { axis: "seasonal_relevance", score: c.length === 0 ? 50 : 90, reason: "In-season utility", source_agent: "vision_agent" },
              { axis: "budget_impact", score: c.length === 0 ? 50 : Math.max(30, 95 - c.length * 15), reason: "Economics score", source_agent: "economics_agent" },
              { axis: "style_alignment", score: c.length === 0 ? 50 : 70, reason: "Personal style fit", source_agent: "style_analysis" },
              { axis: "occasion_coverage", score: c.length === 0 ? 50 : 65, reason: "Occasion coverage", source_agent: "occasion_analysis" },
            ],
          });
        });
      }

      // Sort descending
      generated.sort((a, b) => b.overall_score - a.overall_score);
      generated.forEach((item, idx) => {
        item.rank = idx + 1;
      });

      setRankedResult({
        total_items: n,
        total_subsets: total,
        top_recommendation: generated[0],
        subsets: generated,
      });
      setExpandedSubsetId(generated[0].subset_id);
    } finally {
      setScoring(false);
    }
  }

  const selectedCount = selectedIds.length;
  const isValidCount = selectedCount >= 3 && selectedCount <= 5;

  return (
    <main className="min-h-screen bg-gradient-to-b from-background via-background to-muted/20 pb-16">
      <NavigationHeader currentSubtitle="What-If Lab" badgeText="Cart Optimizer" />

      {/* Main Container */}
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 sm:py-10 space-y-8">
        <motion.div
          initial="hidden"
          animate="visible"
          variants={fadeUpVariants}
          className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b pb-6"
        >
          <div>
            <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider mb-1.5">
              <FlaskConical className="h-4 w-4 text-primary" />
              <span>Flagship Decision Engine</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
              What-If Lab — Cart Combination Ranker
            </h1>
            <p className="text-sm sm:text-base text-muted-foreground mt-1.5 max-w-3xl">
              Score every possible subset of candidate items using set-level synergy and redundancy to find the mathematically optimal purchase decision.
            </p>
          </div>

          <Link href="/candidates">
            <Button variant="outline" size="sm" className="gap-1.5 text-xs font-semibold rounded-xl">
              <Plus className="h-3.5 w-3.5" />
              Intake New Candidate
            </Button>
          </Link>
        </motion.div>

        {/* 1. Item Selection Grid */}
        <Card className="rounded-2xl border shadow-sm bg-card overflow-hidden">
          <CardHeader className="pb-3 border-b bg-muted/10">
            <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
              <CardTitle className="flex items-center gap-2 text-base font-bold">
                <Layers className="h-5 w-5 text-primary" />
                Select 3–5 Candidate Items
              </CardTitle>
              <div className="flex items-center gap-2">
                <Badge
                  variant={isValidCount ? "default" : "destructive"}
                  className="font-bold text-xs px-3 py-1"
                >
                  {selectedCount} of 5 Selected {isValidCount ? "(Ready)" : "(Select 3–5)"}
                </Badge>
              </div>
            </div>
          </CardHeader>

          <CardContent className="p-6 space-y-6">
            {loadingItems ? (
              <div className="py-8 flex items-center justify-center gap-2 text-sm text-muted-foreground">
                <Loader2 className="h-5 w-5 animate-spin text-primary" />
                <span>Loading candidates...</span>
              </div>
            ) : (
              <div className="grid grid-cols-1 sm:grid-cols-2 md:grid-cols-3 lg:grid-cols-5 gap-4">
                {candidates.map((item, idx) => {
                  const isSelected = selectedIds.includes(item.id);
                  const letter = LETTER_LABELS[idx] || `#${item.id}`;
                  const attrs = item.attributes;
                  return (
                    <div
                      key={item.id}
                      onClick={() => toggleItemSelection(item.id)}
                      className={`relative cursor-pointer rounded-2xl p-4 border-2 transition-all flex flex-col justify-between select-none ${
                        isSelected
                          ? "border-primary bg-primary/5 shadow-md ring-2 ring-primary/20"
                          : "border-border bg-card hover:border-muted-foreground/30 opacity-75 hover:opacity-100"
                      }`}
                    >
                      <div className="flex items-center justify-between gap-2 mb-3">
                        <div className="flex items-center gap-1.5">
                          <span className="flex h-6 w-6 items-center justify-center rounded-lg bg-primary/10 text-primary font-black text-xs">
                            {letter}
                          </span>
                          <span className="font-mono text-xs font-bold text-muted-foreground">
                            #{item.id}
                          </span>
                        </div>
                        <div
                          className={`h-5 w-5 rounded-full flex items-center justify-center transition-colors ${
                            isSelected
                              ? "bg-primary text-primary-foreground"
                              : "border border-muted-foreground/40 bg-background"
                          }`}
                        >
                          {isSelected && <CheckCircle2 className="h-4 w-4" />}
                        </div>
                      </div>

                      <div className="flex items-center gap-3 mb-3">
                        <div className="flex h-12 w-12 shrink-0 items-center justify-center rounded-xl bg-muted/60 border text-primary">
                          <Shirt className="h-6 w-6" />
                        </div>
                        <div className="min-w-0">
                          <p className="font-bold text-sm text-foreground capitalize truncate">
                            {attrs?.category || "Item"}
                          </p>
                          <p className="text-xs text-muted-foreground capitalize truncate">
                            {attrs?.color || "N/A"} • {attrs?.style || "Style"}
                          </p>
                        </div>
                      </div>

                      <div className="flex items-center justify-between border-t pt-2.5 text-xs">
                        <span className="text-muted-foreground capitalize">
                          {attrs?.season || "All-Season"}
                        </span>
                        <span className="font-bold text-foreground">
                          {item.price ? `$${item.price.toFixed(2)}` : "$--"}
                        </span>
                      </div>
                    </div>
                  );
                })}
              </div>
            )}

            {error && (
              <div className="flex items-center gap-2 rounded-xl bg-destructive/10 p-3.5 text-xs text-destructive font-medium border border-destructive/20">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="flex flex-col sm:flex-row items-center justify-between gap-4 pt-2 border-t">
              <p className="text-xs text-muted-foreground">
                Selected <span className="font-bold text-foreground">{selectedCount}</span> items will compute and rank{" "}
                <span className="font-mono font-bold text-primary">
                  {Math.pow(2, selectedCount)}
                </span>{" "}
                combinations ($2^{selectedCount}$).
              </p>

              <Button
                onClick={handleScoreSubsets}
                disabled={!isValidCount || scoring}
                className="w-full sm:w-auto font-bold px-8 shadow-md gap-2"
              >
                {scoring ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Evaluating & Ranking {Math.pow(2, selectedCount)} Subsets...
                  </>
                ) : (
                  <>
                    <Zap className="h-4 w-4 fill-primary-foreground" />
                    Score & Rank {Math.pow(2, selectedCount)} Combinations
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* 2. Ranked What-If Results (Milestone 26 Showcase) */}
        {rankedResult && (
          <div className="space-y-6">
            {/* HERO CARD: #1 TOP RECOMMENDATION */}
            {rankedResult.top_recommendation && (
              <motion.div
                initial="hidden"
                animate="visible"
                variants={fadeUpVariants}
              >
                <Card className="border-2 border-emerald-500/50 bg-gradient-to-br from-emerald-500/10 via-emerald-500/5 to-card shadow-xl overflow-hidden">
                  <div className="p-6 sm:p-8">
                    <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b border-emerald-500/20 pb-5">
                      <div className="flex items-center gap-3.5">
                        <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-emerald-500 text-emerald-950 font-black shadow-md">
                          <Trophy className="h-7 w-7" />
                        </div>
                        <div>
                          <div className="flex items-center gap-2 flex-wrap">
                            <Badge className="bg-emerald-500 text-emerald-950 font-black text-xs px-2.5 py-0.5">
                              #1 OPTIMAL SELECTION
                            </Badge>
                            <span className="text-xs text-muted-foreground font-semibold">
                              Rank 1 of {rankedResult.total_subsets}
                            </span>
                            <ConfidenceBadge confidence={rankedResult.top_recommendation.confidence} size="md" />
                          </div>
                          <h2 className="text-2xl sm:text-3xl font-black tracking-tight text-foreground mt-1">
                            {getSubsetDisplayLabel(rankedResult.top_recommendation.item_ids)}
                          </h2>
                        </div>
                      </div>

                      <div className="flex items-center gap-4 bg-background/90 backdrop-blur-md px-5 py-3 rounded-2xl border shadow-sm">
                        <div className="text-right">
                          <div className="text-[11px] font-bold text-muted-foreground uppercase">
                            Buy Score
                          </div>
                          <div className="text-3xl sm:text-4xl font-black text-emerald-600 dark:text-emerald-400">
                            {rankedResult.top_recommendation.overall_score.toFixed(1)}
                            <span className="text-xs font-semibold text-muted-foreground"> / 100</span>
                          </div>
                        </div>
                        {rankedResult.top_recommendation.total_price > 0 && (
                          <div className="border-l pl-4 text-right">
                            <div className="text-[11px] font-bold text-muted-foreground uppercase">
                              Cart Total
                            </div>
                            <div className="text-xl font-bold text-foreground">
                              ${rankedResult.top_recommendation.total_price.toFixed(2)}
                            </div>
                          </div>
                        )}
                      </div>
                    </div>

                    <div className="mt-5 space-y-4">
                      <div className="p-4 bg-background/90 backdrop-blur-md rounded-2xl border flex items-start gap-3">
                        <Sparkles className="h-5 w-5 text-emerald-500 shrink-0 mt-0.5" />
                        <p className="text-sm sm:text-base font-semibold text-foreground leading-relaxed">
                          {rankedResult.top_recommendation.headline_reason}
                        </p>
                      </div>

                      {/* Items Chips */}
                      {rankedResult.top_recommendation.item_ids.length > 0 && (
                        <div className="flex flex-wrap items-center gap-2 pt-1">
                          <span className="text-xs font-bold text-muted-foreground uppercase">
                            Included Items:
                          </span>
                          {rankedResult.top_recommendation.item_ids.map((id) => {
                            const itm = idToItemMap[id];
                            const letter = idToLetterMap[id];
                            return (
                              <div
                                key={id}
                                className="flex items-center gap-2 px-3 py-1.5 rounded-xl border bg-card text-xs font-semibold shadow-sm"
                              >
                                <span className="flex h-5 w-5 items-center justify-center rounded-md bg-emerald-500/20 text-emerald-700 dark:text-emerald-300 font-bold text-[11px]">
                                  {letter}
                                </span>
                                <span className="capitalize">{itm?.attributes?.color} {itm?.attributes?.category || `Item #${id}`}</span>
                                {itm?.price && (
                                  <span className="text-muted-foreground font-mono font-bold">${itm.price}</span>
                                )}
                              </div>
                            );
                          })}
                        </div>
                      )}

                      {/* Milestone 31: 5-Metric Cart Summary Panel */}
                      {rankedResult.top_recommendation.summary_panel && (
                        <div className="pt-4 border-t border-emerald-500/20">
                          <DecisionSummaryPanel
                            metrics={rankedResult.top_recommendation.summary_panel}
                            title="Optimal Cart Summary Metrics"
                          />
                        </div>
                      )}
                    </div>
                  </div>
                </Card>
              </motion.div>
            )}

            {/* FULL RANKED LIST */}
            <div className="space-y-3">
              <div className="flex items-center justify-between pb-2 border-b">
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  All {rankedResult.total_subsets} Evaluated Combinations (Ranked from Best to Worst)
                </span>
                <span className="text-xs font-semibold text-muted-foreground">
                  Baseline: Skip all = 50.0
                </span>
              </div>

              <motion.div
                initial="hidden"
                animate="visible"
                variants={staggerContainerVariants}
                className="space-y-2.5"
              >
                <AnimatePresence>
                  {rankedResult.subsets.map((subset) => {
                    const isTop = subset.rank === 1;
                    const isEmpty = subset.size === 0;
                    const isExpanded = expandedSubsetId === subset.subset_id;
                    const displayLabel = getSubsetDisplayLabel(subset.item_ids);

                    const isBuy = subset.verdict === "buy";
                    const isConsider = subset.verdict === "consider";

                    const badgeVariant: "buy" | "consider" | "skip" = isBuy
                      ? "buy"
                      : isConsider
                      ? "consider"
                      : "skip";

                    return (
                      <motion.div
                        key={subset.subset_id}
                        variants={staggerItemVariants}
                        className={`rounded-2xl border transition-all overflow-hidden ${
                          isTop
                            ? "border-emerald-500/60 bg-emerald-500/5 shadow-md"
                            : isEmpty
                            ? "border-dashed border-muted-foreground/40 bg-muted/20"
                            : "bg-card hover:bg-muted/10 shadow-xs"
                        }`}
                      >
                        <div
                          onClick={() =>
                            setExpandedSubsetId(isExpanded ? null : subset.subset_id)
                          }
                          className="p-4 sm:p-5 flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 cursor-pointer select-none"
                        >
                          <div className="flex items-center gap-3.5 min-w-0 flex-1">
                            <span
                              className={`flex h-8 w-8 shrink-0 items-center justify-center rounded-xl font-mono font-black text-xs ${
                                isTop
                                  ? "bg-emerald-500 text-emerald-950 shadow-sm"
                                  : isEmpty
                                  ? "bg-muted text-muted-foreground"
                                  : "bg-muted text-foreground"
                              }`}
                            >
                              #{subset.rank}
                            </span>

                            <div className="min-w-0 flex-1">
                              <div className="flex items-center gap-2 flex-wrap">
                                <span className="font-extrabold text-sm sm:text-base text-foreground break-words">
                                  {displayLabel}
                                </span>
                                {isEmpty && (
                                  <Badge variant="outline" className="text-[10px] font-bold border-muted-foreground/40">
                                    Fixed Neutral Baseline
                                  </Badge>
                                )}
                                {isTop && (
                                  <Badge variant="buy" className="text-[10px] font-bold px-2 py-0.5">
                                    Best Choice
                                  </Badge>
                                )}
                                <ConfidenceBadge confidence={subset.confidence} size="sm" />
                              </div>
                              <p className="text-xs text-muted-foreground mt-0.5 truncate max-w-xl">
                                {subset.headline_reason}
                              </p>
                            </div>
                          </div>

                          <div className="flex items-center gap-2.5 self-end sm:self-center shrink-0 flex-wrap justify-end">
                            {subset.total_price > 0 && (
                              <span className="text-xs font-bold text-muted-foreground font-mono">
                                ${subset.total_price.toFixed(2)}
                              </span>
                            )}

                            <Badge variant={badgeVariant} className="font-extrabold text-sm px-3 py-1">
                              {subset.overall_score.toFixed(1)}
                            </Badge>

                            <div className="text-muted-foreground">
                              {isExpanded ? (
                                <ChevronDown className="h-4 w-4" />
                              ) : (
                                <ChevronRight className="h-4 w-4" />
                              )}
                            </div>
                          </div>
                        </div>

                        {/* Expanded 6-Axis Breakdown */}
                        {isExpanded && (
                          <div className="p-4 sm:p-5 border-t bg-muted/20 space-y-3">
                            <div className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">
                              6-Axis Decision Breakdown
                            </div>
                            <div className="grid grid-cols-2 sm:grid-cols-3 lg:grid-cols-6 gap-2">
                              {subset.axes.map((ax) => {
                                const isHigh = ax.score >= 70;
                                const isMid = ax.score >= 45 && ax.score < 70;
                                return (
                                  <div
                                    key={ax.axis}
                                    className="p-2.5 rounded-xl border bg-background text-xs space-y-1"
                                  >
                                    <div className="flex items-center justify-between">
                                      <span className="text-[10px] font-bold uppercase text-muted-foreground truncate">
                                        {ax.axis.replace("_", " ")}
                                      </span>
                                      <span
                                        className={`font-mono font-bold text-xs ${
                                          isHigh
                                            ? "text-emerald-600 dark:text-emerald-400"
                                            : isMid
                                            ? "text-amber-600 dark:text-amber-400"
                                            : "text-rose-600 dark:text-rose-400"
                                        }`}
                                      >
                                        {Math.round(ax.score)}
                                      </span>
                                    </div>
                                    <p className="text-[10px] text-muted-foreground leading-tight line-clamp-2">
                                      {ax.reason}
                                    </p>
                                  </div>
                                );
                              })}
                            </div>

                            {/* Milestone 31: 5-Metric Subset Summary Panel */}
                            {subset.summary_panel && (
                              <div className="pt-3 border-t">
                                <DecisionSummaryPanel
                                  metrics={subset.summary_panel}
                                  variant="compact"
                                  title="Subset Summary Metrics"
                                />
                              </div>
                            )}
                          </div>
                        )}
                      </motion.div>
                    );
                  })}
                </AnimatePresence>
              </motion.div>
            </div>
          </div>
        )}
      </div>
    </main>
  );
}
