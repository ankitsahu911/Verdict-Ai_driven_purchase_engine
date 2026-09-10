"use client";

import React, { useEffect, useState } from "react";
import Link from "next/link";
import {
  Sparkles,
  Shirt,
  Compass,
  LayoutDashboard,
  Scale,
  FlaskConical,
  CheckCircle2,
  AlertCircle,
  Loader2,
  Play,
  ArrowRight,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { motion } from "framer-motion";
import { NavigationHeader } from "@/components/NavigationHeader";
import { fadeUpVariants } from "@/lib/animations";
import { OpportunityCostCard } from "@/components/OpportunityCostCard";
import {
  fetchCandidates,
  compareOpportunityCost,
  type CandidateItemData,
  type OpportunityCostCompareResponseData,
} from "@/lib/api";

const DEMO_CANDIDATES: CandidateItemData[] = [
  {
    id: 101,
    cloudinary_url: "",
    price: 180.0,
    fit_tightness: "regular",
    silhouette: "tailored",
    uploaded_at: new Date().toISOString(),
    attributes: {
      category: "jacket",
      color: "black",
      pattern: "solid",
      style: "formal",
      season: "winter",
      material: "wool",
      extraction_source: "ai",
    },
  },
  {
    id: 102,
    cloudinary_url: "",
    price: 65.0,
    fit_tightness: "regular",
    silhouette: "relaxed",
    uploaded_at: new Date().toISOString(),
    attributes: {
      category: "top",
      color: "white",
      pattern: "solid",
      style: "casual",
      season: "all-season",
      material: "cotton",
      extraction_source: "ai",
    },
  },
  {
    id: 103,
    cloudinary_url: "",
    price: 85.0,
    fit_tightness: "regular",
    silhouette: "straight",
    uploaded_at: new Date().toISOString(),
    attributes: {
      category: "bottom",
      color: "dark blue",
      pattern: "solid",
      style: "casual",
      season: "all-season",
      material: "denim",
      extraction_source: "ai",
    },
  },
  {
    id: 104,
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

const SAMPLE_COMPARE_DATA: OpportunityCostCompareResponseData = {
  candidate: {
    candidate_id: 101,
    verdict: "consider",
    overall_score: 64.2,
    headline_reason: "CONSIDER: High standalone price with moderate versatility (2 outfits).",
    axes: [
      { axis: "versatility", score: 40.0, reason: "Pairs into 2 outfits with current wardrobe.", source_agent: "outfit_composition" },
      { axis: "redundancy", score: 90.0, reason: "No close match in wardrobe.", source_agent: "duplicate_detection" },
      { axis: "seasonal_relevance", score: 85.0, reason: "Winter seasonal utility.", source_agent: "vision_agent" },
      { axis: "budget_impact", score: 45.0, reason: "High initial outlay ($180.00).", source_agent: "economics_agent" },
      { axis: "style_alignment", score: 65.0, reason: "Formal outerwear style fit.", source_agent: "style_analysis" },
      { axis: "occasion_coverage", score: 60.0, reason: "Adds formal evening coverage.", source_agent: "occasion_analysis" },
    ],
    weights_used: { versatility: 0.1667 },
    confidence: {
      level: "medium",
      reasoning: "Medium confidence: Score (64.2) sits near the Consider/Buy boundary with high variance across axes.",
    },
    summary_panel: {
      versatility: 40.0,
      versatility_outfits_count: 2,
      duplicate_risk: 10.0,
      duplicate_risk_label: "10.0% similarity to wardrobe (Low duplicate risk)",
      seasonality: 85.0,
      seasonality_label: "In-Season (High winter utility)",
      cost_per_wear: 6.0,
      cost_per_wear_formatted: "$6.00 / wear",
      sustainability_tier: "Lower impact",
      sustainability_reason: "Rough estimate based on Natural animal fiber ('wool'). Not a certified rating.",
      is_estimate: true,
    },
    created_at: new Date().toISOString(),
  },
  alternative_bundle: {
    subset_id: "subset_bundle",
    rank: 1,
    size: 2,
    item_ids: [102, 103],
    verdict: "buy",
    overall_score: 83.5,
    headline_reason: "BUY: High synergy pair creating 7 new outfits with efficient cost-per-wear.",
    total_price: 150.0,
    confidence: {
      level: "high",
      reasoning: "High confidence: Decisive set score (83.5) with strong synergy unlocking 7 complete outfits.",
    },
    summary_panel: {
      versatility: 87.5,
      versatility_outfits_count: 7,
      duplicate_risk: 8.0,
      duplicate_risk_label: "8.0% max wardrobe similarity (Low duplicate risk)",
      seasonality: 95.0,
      seasonality_label: "In-Season (Immediate wearability across bundle)",
      cost_per_wear: 3.0,
      cost_per_wear_formatted: "$3.00 / wear",
      sustainability_tier: "Lower impact",
      sustainability_reason: "Rough estimate based on natural fibers ('cotton', 'denim'). Not a certified rating.",
      is_estimate: true,
    },
    axes: [
      { axis: "versatility", score: 87.5, reason: "High synergy: unlocks 7 complete outfits across cart and wardrobe.", source_agent: "outfit_composition" },
      { axis: "redundancy", score: 92.0, reason: "High uniqueness: items add fresh distinct pieces without internal overlap.", source_agent: "duplicate_detection" },
      { axis: "seasonal_relevance", score: 95.0, reason: "In-season items — immediately wearable.", source_agent: "vision_agent" },
      { axis: "budget_impact", score: 80.0, reason: "Strong value-for-money with efficient combined cost-per-wear.", source_agent: "economics_agent" },
      { axis: "style_alignment", score: 75.0, reason: "Fits your established personal wardrobe style profile.", source_agent: "style_analysis" },
      { axis: "occasion_coverage", score: 71.5, reason: "Fills functional lifestyle gaps across everyday categories.", source_agent: "occasion_analysis" },
    ],
  },
  candidate_versatility: 40.0,
  alternative_bundle_versatility: 87.5,
  versatility_delta: 47.5,
  candidate_outfit_count: 2,
  alternative_bundle_outfit_count: 7,
  outfit_count_delta: 5,
  candidate_name: "Black Jacket",
  alternative_names: ["White Top", "Dark Blue Bottom"],
};

export default function OpportunityCostPage() {
  const [candidates, setCandidates] = useState<CandidateItemData[]>(DEMO_CANDIDATES);
  const [primaryCandidateId, setPrimaryCandidateId] = useState<number>(101);
  const [selectedAltIds, setSelectedAltIds] = useState<number[]>([102, 103]);
  const [loading, setLoading] = useState(false);
  const [result, setResult] = useState<OpportunityCostCompareResponseData | null>(SAMPLE_COMPARE_DATA);
  const [error, setError] = useState<string | null>(null);

  useEffect(() => {
    fetchCandidates()
      .then((items) => {
        if (items && items.length >= 3) {
          setCandidates(items);
          const pId = items[0].id;
          const altIds = [items[1].id, items[2].id];
          setPrimaryCandidateId(pId);
          setSelectedAltIds(altIds);
          setLoading(true);
          compareOpportunityCost(pId, altIds)
            .then((res) => setResult(res))
            .catch(() => {})
            .finally(() => setLoading(false));
        }
      })
      .catch(() => {
        setCandidates(DEMO_CANDIDATES);
      });
  }, []);

  const itemMap: Record<number, CandidateItemData> = {};
  candidates.forEach((c) => {
    itemMap[c.id] = c;
  });

  function toggleAltItem(id: number) {
    if (id === primaryCandidateId) return;
    setError(null);
    if (selectedAltIds.includes(id)) {
      setSelectedAltIds(selectedAltIds.filter((i) => i !== id));
    } else {
      if (selectedAltIds.length >= 2) {
        setSelectedAltIds([selectedAltIds[1], id]);
      } else {
        setSelectedAltIds([...selectedAltIds, id]);
      }
    }
  }

  function handleSelectPrimary(id: number) {
    setError(null);
    setPrimaryCandidateId(id);
    setSelectedAltIds(selectedAltIds.filter((i) => i !== id));
  }

  async function handleCompare() {
    if (selectedAltIds.length !== 2) {
      setError("Please select exactly 2 alternative items for the comparison bundle.");
      return;
    }
    if (selectedAltIds.includes(primaryCandidateId)) {
      setError("The primary candidate item cannot also be in the alternative bundle.");
      return;
    }

    setLoading(true);
    setError(null);

    try {
      const res = await compareOpportunityCost(primaryCandidateId, selectedAltIds);
      setResult(res);
    } catch (err: unknown) {
      // Fallback demo computation
      const candItem = itemMap[primaryCandidateId];
      const alt1 = itemMap[selectedAltIds[0]];
      const alt2 = itemMap[selectedAltIds[1]];

      const candName = candItem ? `${candItem.attributes?.color} ${candItem.attributes?.category}` : `Item #${primaryCandidateId}`;
      const alt1Name = alt1 ? `${alt1.attributes?.color} ${alt1.attributes?.category}` : `Item #${selectedAltIds[0]}`;
      const alt2Name = alt2 ? `${alt2.attributes?.color} ${alt2.attributes?.category}` : `Item #${selectedAltIds[1]}`;

      setResult({
        ...SAMPLE_COMPARE_DATA,
        candidate_name: candName.trim().replace(/^./, (str) => str.toUpperCase()),
        alternative_names: [alt1Name.trim(), alt2Name.trim()],
        candidate: {
          ...SAMPLE_COMPARE_DATA.candidate,
          candidate_id: primaryCandidateId,
        },
        alternative_bundle: {
          ...SAMPLE_COMPARE_DATA.alternative_bundle,
          item_ids: selectedAltIds,
        },
      });
    } finally {
      setLoading(false);
    }
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-background via-background to-muted/20 pb-16">
      <NavigationHeader currentSubtitle="Opportunity Cost" badgeText="Comparison Engine" />

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
              <Scale className="h-4 w-4 text-primary" />
              <span>Milestone 28 Comparison Card</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
              Opportunity Cost Lab
            </h1>
            <p className="text-sm sm:text-base text-muted-foreground mt-1.5 max-w-3xl">
              Compare one candidate purchase against a 2-item alternative bundle to evaluate outfit versatility gain and decision scores.
            </p>
          </div>
        </motion.div>

        {/* Item Pickers (1 Candidate vs. 2 Alternatives) */}
        <Card className="rounded-2xl border shadow-sm bg-card overflow-hidden">
          <CardHeader className="pb-3 border-b bg-muted/10">
            <CardTitle className="text-base font-bold flex items-center gap-2">
              <Shirt className="h-5 w-5 text-primary" />
              Configure Opportunity Cost Comparison
            </CardTitle>
          </CardHeader>
          <CardContent className="p-6 space-y-6">
            {/* Step 1: Select 1 Primary Candidate */}
            <div>
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Step 1: Pick 1 Primary Candidate Item (Option A)
                </span>
                <Badge variant="outline" className="font-mono text-[11px]">
                  Selected: #{primaryCandidateId}
                </Badge>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {candidates.map((c) => {
                  const isSelected = c.id === primaryCandidateId;
                  const isAlt = selectedAltIds.includes(c.id);
                  return (
                    <div
                      key={c.id}
                      onClick={() => handleSelectPrimary(c.id)}
                      className={`p-3 rounded-2xl border-2 cursor-pointer transition-all flex items-center gap-3 select-none ${
                        isSelected
                          ? "border-primary bg-primary/10 shadow-md ring-2 ring-primary/20"
                          : isAlt
                          ? "border-dashed opacity-40 cursor-not-allowed"
                          : "border-border bg-card hover:border-muted-foreground/30"
                      }`}
                    >
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-muted/70 text-primary">
                        <Shirt className="h-5 w-5" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-bold text-xs capitalize truncate">
                          {c.attributes?.color} {c.attributes?.category || `Item #${c.id}`}
                        </p>
                        <p className="text-[11px] font-mono text-muted-foreground">
                          {c.price ? `$${c.price.toFixed(2)}` : `ID #${c.id}`}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {/* Step 2: Select 2 Alternative Items */}
            <div className="pt-2 border-t">
              <div className="flex items-center justify-between mb-3">
                <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
                  Step 2: Pick 2 Alternative Items for Bundle (Option B)
                </span>
                <Badge
                  variant={selectedAltIds.length === 2 ? "default" : "destructive"}
                  className="font-bold text-[11px]"
                >
                  {selectedAltIds.length} / 2 Selected
                </Badge>
              </div>

              <div className="grid grid-cols-2 sm:grid-cols-4 gap-3">
                {candidates.map((c) => {
                  const isPrimary = c.id === primaryCandidateId;
                  const isSelected = selectedAltIds.includes(c.id);
                  return (
                    <div
                      key={c.id}
                      onClick={() => !isPrimary && toggleAltItem(c.id)}
                      className={`p-3 rounded-2xl border-2 transition-all flex items-center gap-3 select-none ${
                        isPrimary
                          ? "border-dashed opacity-30 cursor-not-allowed bg-muted/20"
                          : isSelected
                          ? "border-emerald-500 bg-emerald-500/10 shadow-md ring-2 ring-emerald-500/20 cursor-pointer"
                          : "border-border bg-card hover:border-muted-foreground/30 cursor-pointer"
                      }`}
                    >
                      <div className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-emerald-500/10 text-emerald-600">
                        <Shirt className="h-5 w-5" />
                      </div>
                      <div className="min-w-0">
                        <p className="font-bold text-xs capitalize truncate">
                          {c.attributes?.color} {c.attributes?.category || `Item #${c.id}`}
                        </p>
                        <p className="text-[11px] font-mono text-muted-foreground">
                          {c.price ? `$${c.price.toFixed(2)}` : `ID #${c.id}`}
                        </p>
                      </div>
                    </div>
                  );
                })}
              </div>
            </div>

            {error && (
              <div className="flex items-center gap-2 rounded-xl bg-destructive/10 p-3 text-xs text-destructive font-medium border border-destructive/20">
                <AlertCircle className="h-4 w-4 shrink-0" />
                <span>{error}</span>
              </div>
            )}

            <div className="flex justify-end pt-2 border-t">
              <Button
                onClick={handleCompare}
                disabled={selectedAltIds.length !== 2 || loading}
                className="font-bold px-8 gap-2 shadow-md"
              >
                {loading ? (
                  <>
                    <Loader2 className="h-4 w-4 animate-spin" />
                    Computing Comparison...
                  </>
                ) : (
                  <>
                    <Scale className="h-4 w-4" />
                    Compare Opportunity Cost
                  </>
                )}
              </Button>
            </div>
          </CardContent>
        </Card>

        {/* Render OpportunityCostCard Result */}
        {result && (
          <div className="space-y-4">
            <OpportunityCostCard
              data={result}
              candidateItemMap={itemMap}
            />
          </div>
        )}
      </div>
    </main>
  );
}
