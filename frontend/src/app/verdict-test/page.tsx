"use client";

import React, { useState } from "react";
import Link from "next/link";
import { Sparkles, ArrowRight, ShieldCheck, Shirt, LayoutDashboard, Compass } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Badge } from "@/components/ui/badge";
import { NavigationHeader } from "@/components/NavigationHeader";
import { fadeUpVariants } from "@/lib/animations";
import { motion } from "framer-motion";
import { VerdictCard } from "@/components/VerdictCard";
import type { BuyScoreResultData } from "@/lib/api";

const DEMO_ITEMS: Record<string, BuyScoreResultData> = {
  buy: {
    candidate_id: 101,
    verdict: "buy",
    overall_score: 82.5,
    headline_reason:
      "BUY: Fall item, currently in season (October) — immediately wearable.",
    axes: [
      {
        axis: "versatility",
        score: 85.0,
        reason: "Pairs into 4 complete outfits with items you already own.",
        source_agent: "outfit_composition",
      },
      {
        axis: "redundancy",
        score: 92.0,
        reason: "No close match in your current wardrobe (very unique).",
        source_agent: "duplicate_detection",
      },
      {
        axis: "seasonal_relevance",
        score: 100.0,
        reason: "Fall item, currently in season (October) — immediately wearable.",
        source_agent: "vision_agent",
      },
      {
        axis: "budget_impact",
        score: 88.0,
        reason: "Efficient cost-per-wear ($2.10/wear vs $3.50 ceiling) with low predicted return risk (15%).",
        source_agent: "economics_agent",
      },
      {
        axis: "style_alignment",
        score: 70.0,
        reason: "70.0% of your wardrobe is already casual — fits your established personal style.",
        source_agent: "style_analysis",
      },
      {
        axis: "occasion_coverage",
        score: 60.0,
        reason: "Expands your casual everyday occasion coverage.",
        source_agent: "occasion_analysis",
      },
    ],
    weights_used: {
      versatility: 0.1667,
      redundancy: 0.1667,
      seasonal_relevance: 0.1667,
      budget_impact: 0.1667,
      style_alignment: 0.1667,
      occasion_coverage: 0.1667,
    },
    confidence: {
      level: "high",
      reasoning: "High confidence: Decisive score far from decision boundaries, strong consensus across all 6 axes, and unambiguous category classification.",
    },
    created_at: new Date().toISOString(),
  },
  consider: {
    candidate_id: 102,
    verdict: "consider",
    overall_score: 58.3,
    headline_reason:
      "CONSIDER: 60.0% of your wardrobe is already formal — this fits your style. (Though note: High cost-per-wear ($18.00/wear vs $15.00 ceiling).)",
    axes: [
      {
        axis: "versatility",
        score: 50.0,
        reason: "Pairs into 2 complete formal outfits with items you already own.",
        source_agent: "outfit_composition",
      },
      {
        axis: "redundancy",
        score: 75.0,
        reason: "25.0% similarity to existing formal items in your wardrobe.",
        source_agent: "duplicate_detection",
      },
      {
        axis: "seasonal_relevance",
        score: 60.0,
        reason: "Winter item, and it's currently October (2 months away) — upcoming.",
        source_agent: "vision_agent",
      },
      {
        axis: "budget_impact",
        score: 35.0,
        reason: "High cost-per-wear ($18.00/wear vs $15.00 ceiling) with elevated return risk (45%).",
        source_agent: "economics_agent",
      },
      {
        axis: "style_alignment",
        score: 60.0,
        reason: "60.0% of your wardrobe is already formal — this fits your style.",
        source_agent: "style_analysis",
      },
      {
        axis: "occasion_coverage",
        score: 40.0,
        reason: "40.0% of your wardrobe is already formal — adds little new occasion coverage.",
        source_agent: "occasion_analysis",
      },
    ],
    weights_used: {
      versatility: 0.1667,
      redundancy: 0.1667,
      seasonal_relevance: 0.1667,
      budget_impact: 0.1667,
      style_alignment: 0.1667,
      occasion_coverage: 0.1667,
    },
    confidence: {
      level: "medium",
      reasoning: "Medium confidence: Decision axes exhibit moderate variance (spread of 40.0 pts) across budget and uniqueness.",
    },
    created_at: new Date().toISOString(),
  },
  skip: {
    candidate_id: 103,
    verdict: "skip",
    overall_score: 31.7,
    headline_reason:
      "SKIP: All-season item — wearable year-round. (Though note: 88.0% similar to an item you already own — largely redundant.)",
    axes: [
      {
        axis: "versatility",
        score: 20.0,
        reason: "Pairs into only 1 outfit with your current wardrobe.",
        source_agent: "outfit_composition",
      },
      {
        axis: "redundancy",
        score: 12.0,
        reason: "88.0% similar to an item you already own — largely redundant.",
        source_agent: "duplicate_detection",
      },
      {
        axis: "seasonal_relevance",
        score: 95.0,
        reason: "All-season item — wearable year-round.",
        source_agent: "vision_agent",
      },
      {
        axis: "budget_impact",
        score: 20.0,
        reason: "High cost-per-wear ($9.00/wear vs $3.50 ceiling) with tight fit signal.",
        source_agent: "economics_agent",
      },
      {
        axis: "style_alignment",
        score: 20.0,
        reason: "None of your current wardrobe is athletic — low style alignment.",
        source_agent: "style_analysis",
      },
      {
        axis: "occasion_coverage",
        score: 23.0,
        reason: "Adds minimal functional coverage to your lifestyle.",
        source_agent: "occasion_analysis",
      },
    ],
    weights_used: {
      versatility: 0.1667,
      redundancy: 0.1667,
      seasonal_relevance: 0.1667,
      budget_impact: 0.1667,
      style_alignment: 0.1667,
      occasion_coverage: 0.1667,
    },
    confidence: {
      level: "low",
      reasoning: "Low confidence: Decision axes exhibit high disagreement with a spread of 83.0 pts, and 'athletic' is a borderline category boundary.",
    },
    created_at: new Date().toISOString(),
  },
};

export default function VerdictTestPage() {
  const [selectedDemo, setSelectedDemo] = useState<string>("buy");
  const [candidateIdInput, setCandidateIdInput] = useState<string>("");
  const [activeCandidateId, setActiveCandidateId] = useState<number | null>(null);

  function handleLookup(e: React.FormEvent) {
    e.preventDefault();
    const id = parseInt(candidateIdInput.trim(), 10);
    if (!isNaN(id) && id > 0) {
      setActiveCandidateId(id);
      setSelectedDemo("");
    }
  }

  function handleSelectDemo(key: string) {
    setSelectedDemo(key);
    setActiveCandidateId(null);
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-background via-background to-muted/20 pb-16">
      <NavigationHeader currentSubtitle="Verdict Visualizer" badgeText="Decision Engine" />

      {/* Main Full-Frame Content */}
      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 sm:py-10 space-y-8">
        {/* Page Hero Title & Description */}
        <motion.div
          initial="hidden"
          animate="visible"
          variants={fadeUpVariants}
          className="flex flex-col md:flex-row md:items-end justify-between gap-4 border-b pb-6"
        >
          <div>
            <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider mb-1.5">
              <Sparkles className="h-4 w-4 text-primary" />
              <span>Decision Engine Synthesis</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
              The Verdict & 6-Axis Radar Visualizer
            </h1>
            <p className="text-sm sm:text-base text-muted-foreground mt-1.5 max-w-3xl">
              Explore how all 6 decision axes (Versatility, Uniqueness, Timing, Economics, Style Fit, and Wardrobe Gap) synthesize into a single confident verdict.
            </p>
          </div>
        </motion.div>

        {/* Interactive Controls Bar */}
        <Card className="rounded-2xl border shadow-sm bg-card/90 backdrop-blur-sm">
          <CardContent className="p-4 sm:p-5 flex flex-col lg:flex-row items-stretch lg:items-center justify-between gap-4">
            <div className="flex flex-col sm:flex-row sm:items-center gap-3">
              <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground shrink-0">
                Switch Demo Verdict:
              </span>
              <div className="flex flex-wrap gap-2">
                <Button
                  variant={selectedDemo === "buy" ? "default" : "outline"}
                  size="sm"
                  className={selectedDemo === "buy" ? "bg-emerald-600 hover:bg-emerald-700 text-white font-bold shadow-sm" : "font-semibold"}
                  onClick={() => handleSelectDemo("buy")}
                >
                  BUY (82.5)
                </Button>
                <Button
                  variant={selectedDemo === "consider" ? "default" : "outline"}
                  size="sm"
                  className={selectedDemo === "consider" ? "bg-amber-600 hover:bg-amber-700 text-white font-bold shadow-sm" : "font-semibold"}
                  onClick={() => handleSelectDemo("consider")}
                >
                  CONSIDER (58.3)
                </Button>
                <Button
                  variant={selectedDemo === "skip" ? "default" : "outline"}
                  size="sm"
                  className={selectedDemo === "skip" ? "bg-rose-600 hover:bg-rose-700 text-white font-bold shadow-sm" : "font-semibold"}
                  onClick={() => handleSelectDemo("skip")}
                >
                  SKIP (31.7)
                </Button>
              </div>
            </div>

            <form onSubmit={handleLookup} className="flex items-center gap-2">
              <Input
                type="number"
                placeholder="Or Candidate ID..."
                value={candidateIdInput}
                onChange={(e) => setCandidateIdInput(e.target.value)}
                className="w-40 h-9 text-xs"
              />
              <Button type="submit" size="sm" variant="secondary" className="gap-1 text-xs font-semibold">
                Fetch Live <ArrowRight className="h-3.5 w-3.5" />
              </Button>
            </form>
          </CardContent>
        </Card>

        {/* Live / Demo Render */}
        <div className="w-full">
          {activeCandidateId ? (
            <VerdictCard candidateId={activeCandidateId} />
          ) : selectedDemo && DEMO_ITEMS[selectedDemo] ? (
            <VerdictCard initialData={DEMO_ITEMS[selectedDemo]} />
          ) : (
            <p className="text-center text-sm text-muted-foreground py-12">
              Select a demo verdict above or enter a Candidate ID to view.
            </p>
          )}
        </div>
      </div>
    </main>
  );
}
