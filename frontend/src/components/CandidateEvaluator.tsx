"use client";

import React, { useState } from "react";
import {
  Upload,
  Sparkles,
  Shirt,
  UserCheck,
  Layers,
  AlertTriangle,
  Play,
  CheckCircle2,
  Scan,
  Compass,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { NearDuplicateCard } from "@/components/NearDuplicateCard";
import { VerdictCard } from "@/components/VerdictCard";
import {
  getAuthToken,
  evaluateCandidate,
  type CandidateEvaluationResult,
  type BuyScoreResultData,
} from "@/lib/api";

const STAGES = [
  { id: 1, label: "Uploading photo...", icon: Upload },
  { id: 2, label: "Analyzing garment attributes with Vision AI...", icon: Sparkles },
  { id: 3, label: "Generating virtual try-on & fit signals...", icon: UserCheck },
  { id: 4, label: "Checking wardrobe for near-duplicates...", icon: Layers },
];

const SAMPLE_BUY_SCORE_DEMO: BuyScoreResultData = {
  candidate_id: 101,
  verdict: "buy",
  overall_score: 82.5,
  headline_reason:
    "BUY: Fall outerwear piece, currently in season (October) — versatile addition pairing into 4 complete outfits.",
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
      reason: "No close match in your current wardrobe (18.5% similarity — very unique).",
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
    reasoning: "High confidence: Decisive score (82.5), strong axis consensus, and unambiguous outerwear category.",
  },
  created_at: new Date().toISOString(),
};

const SAMPLE_DEMO_RESULT: CandidateEvaluationResult = {
  candidate_item_id: 101,
  cloudinary_url: "",
  attributes: {
    category: "outerwear",
    color: "khaki beige",
    pattern: "solid",
    style: "casual",
    season: "fall",
    material: "cotton twill",
    extraction_source: "ai",
  },
  tryon: {
    render_url: "",
    fit_tightness: "regular",
    silhouette: "tailored",
    notes: "Clean natural shoulder drape with comfortable regular chest fit.",
  },
  duplicate: {
    wardrobe_item_id: 14,
    cloudinary_url: "",
    similarity_percentage: 18.5,
    distance: 0.815,
    category: "top",
    message: "18.5% match to a top in your wardrobe (Unique piece).",
  },
  errors: null,
};

export function CandidateEvaluator() {
  const [file, setFile] = useState<File | null>(null);
  const [price, setPrice] = useState<string>("85.00");
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [currentStage, setCurrentStage] = useState<number>(1);
  const [result, setResult] = useState<CandidateEvaluationResult | null>(SAMPLE_DEMO_RESULT);
  const [error, setError] = useState<string | null>(null);

  function handleFileSelect(e: React.ChangeEvent<HTMLInputElement>) {
    if (e.target.files && e.target.files[0]) {
      const selected = e.target.files[0];
      setFile(selected);
      setPreviewUrl(URL.createObjectURL(selected));
      setResult(null);
      setError(null);
    }
  }

  function handleLoadDemo() {
    setFile(null);
    setPreviewUrl(null);
    setError(null);
    setResult(SAMPLE_DEMO_RESULT);
  }

  async function handleEvaluate() {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setCurrentStage(1);

    const timer1 = setTimeout(() => setCurrentStage(2), 1500);
    const timer2 = setTimeout(() => setCurrentStage(3), 4000);
    const timer3 = setTimeout(() => setCurrentStage(4), 8000);

    try {
      let token = await getAuthToken();
      if (!token) {
        token = "demo-token";
      }

      const numPrice = price ? parseFloat(price) : undefined;
      const res = await evaluateCandidate(file, token, numPrice);
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Candidate evaluation failed");
    } finally {
      clearTimeout(timer1);
      clearTimeout(timer2);
      clearTimeout(timer3);
      setLoading(false);
    }
  }

  return (
    <div className="space-y-8">
      {/* Upload & Controls Card */}
      <Card className="border border-border/80 shadow-md bg-card rounded-2xl">
        <CardHeader className="pb-3 border-b border-border/60 bg-muted/20">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-3">
            <CardTitle className="flex items-center gap-2.5 text-base sm:text-lg font-serif font-bold text-foreground">
              <Shirt className="h-5 w-5 text-neutral-800 dark:text-neutral-200" />
              Add Candidate Garment
            </CardTitle>
            <Button
              variant="outline"
              size="sm"
              onClick={handleLoadDemo}
              className="h-10 px-4 text-xs sm:text-sm font-semibold gap-2 border-border bg-card hover:bg-neutral-100 dark:hover:bg-neutral-800 text-foreground cursor-pointer shadow-xs rounded-xl"
            >
              <Play className="h-3.5 w-3.5 fill-foreground text-foreground" />
              Load Sample Evaluated Candidate
            </Button>
          </div>
        </CardHeader>
        <CardContent className="p-6 space-y-4">
          <div className="flex flex-col lg:flex-row items-center gap-4">
            <label className="flex-1 w-full flex items-center justify-center gap-3 border-2 border-dashed border-border hover:border-foreground/50 rounded-2xl p-4 cursor-pointer transition-colors bg-secondary/40 hover:bg-secondary/70">
              <Upload className="h-5 w-5 text-muted-foreground" />
              <span className="text-sm font-medium text-foreground/80 truncate">
                {file ? file.name : "Choose garment photo or screenshot..."}
              </span>
              <input
                type="file"
                accept="image/jpeg,image/png,image/webp"
                onChange={handleFileSelect}
                disabled={loading}
                className="hidden"
              />
            </label>

            {/* Garment Price Input Field for Cost Per Wear */}
            <div className="w-full lg:w-56 flex items-center rounded-2xl border-2 border-border bg-card px-4 py-3 gap-2 shadow-xs">
              <span className="text-sm font-bold text-muted-foreground">$</span>
              <input
                type="number"
                min="0"
                step="0.01"
                placeholder="Cloth Price ($)"
                value={price}
                onChange={(e) => setPrice(e.target.value)}
                disabled={loading}
                className="w-full bg-transparent text-sm font-bold text-foreground focus:outline-none"
              />
              <span className="text-[11px] font-bold text-muted-foreground uppercase tracking-wider">USD</span>
            </div>

            <Button
              onClick={handleEvaluate}
              disabled={!file || loading}
              size="lg"
              className="w-full lg:w-auto h-12 px-8 font-bold text-sm sm:text-base tracking-wide bg-neutral-900 text-white hover:bg-black dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-100 shadow-md cursor-pointer rounded-2xl"
            >
              {loading ? "Evaluating Pipeline..." : "Run Evaluation"}
            </Button>
          </div>

          {previewUrl && !result && (
            <div className="relative aspect-video max-h-48 w-full max-w-xs overflow-hidden rounded-xl border bg-muted mx-auto shadow-sm">
              <img
                src={previewUrl}
                alt="Selected garment preview"
                className="h-full w-full object-contain"
              />
            </div>
          )}

          {loading && (
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between text-xs text-muted-foreground font-medium">
                <span>Evaluation pipeline in progress</span>
                <span>Stage {currentStage} of 4</span>
              </div>
              <Progress value={currentStage * 25} className="h-2" />

              <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-2">
                {STAGES.map((s) => {
                  const Icon = s.icon;
                  const isActive = s.id === currentStage;
                  const isDone = s.id < currentStage;
                  return (
                    <div
                      key={s.id}
                      className={`flex items-center gap-2 rounded-lg p-2.5 text-xs transition-colors ${
                        isActive
                          ? "bg-primary/10 font-bold text-primary border border-primary/20"
                          : isDone
                          ? "bg-muted text-muted-foreground line-through opacity-70"
                          : "bg-muted/30 text-muted-foreground/60"
                      }`}
                    >
                      <Icon className="h-4 w-4 shrink-0" />
                      <span className="truncate">{s.label.split("...")[0]}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 rounded-xl bg-destructive/10 p-3.5 text-xs text-destructive font-medium border border-destructive/20">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Orchestrated Single-Screen Evaluation Results */}
      {result && (
        <div className="space-y-8">
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-4 border-b pb-4">
            <div className="flex items-center gap-3.5">
              {result.cloudinary_url ? (
                <img
                  src={result.cloudinary_url}
                  alt="Candidate photo"
                  className="h-14 w-14 rounded-2xl object-cover border-2 shadow-sm"
                />
              ) : (
                <div className="flex h-14 w-14 items-center justify-center rounded-2xl bg-primary/10 border-2 border-primary/20 text-primary shadow-sm">
                  <Shirt className="h-7 w-7" />
                </div>
              )}
              <div>
                <h2 className="text-xl font-extrabold text-foreground">Candidate Intake Results</h2>
                <p className="text-xs text-muted-foreground mt-0.5">
                  Item <code className="font-mono font-bold text-primary">#{result.candidate_item_id}</code> evaluated across Vision, Virtual Try-On, Duplicate Search, and Buy Score.
                </p>
              </div>
            </div>
            <Badge className="bg-amber-600/15 text-amber-800 dark:text-amber-200 border-amber-600/30 font-bold text-xs px-3 py-1 shadow-xs">
              <CheckCircle2 className="h-3.5 w-3.5 mr-1" />
              Multi-Agent Evaluation Complete
            </Badge>
          </div>

          {/* Cost-Per-Wear Real-Time Calculation Card */}
          {price && parseFloat(price) > 0 && (
            <div className="grid grid-cols-1 sm:grid-cols-3 gap-3 p-4 rounded-2xl border border-border/80 bg-muted/20 shadow-xs">
              <div className="space-y-0.5">
                <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Cloth Retail Cost</span>
                <p className="text-base sm:text-lg font-bold font-mono text-foreground">${parseFloat(price).toFixed(2)}</p>
                <p className="text-[10px] text-muted-foreground">Original input price</p>
              </div>
              <div className="space-y-0.5 border-t sm:border-t-0 sm:border-l sm:pl-4 border-border/60">
                <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Baseline Usage</span>
                <p className="text-base sm:text-lg font-bold text-foreground">
                  {result.attributes?.category === "outerwear" ? "15 wears/yr" : result.attributes?.category === "bottom" ? "35 wears/yr" : result.attributes?.category === "dress" ? "10 wears/yr" : "30 wears/yr"}
                </p>
                <p className="text-[10px] text-muted-foreground capitalize">{result.attributes?.category || "Standard"} category baseline</p>
              </div>
              <div className="space-y-0.5 border-t sm:border-t-0 sm:border-l sm:pl-4 border-border/60">
                <span className="text-[10px] uppercase font-bold text-amber-800 dark:text-amber-300 tracking-wider">Cost-Per-Wear (CPW)</span>
                <p className="text-base sm:text-lg font-black font-mono text-amber-700 dark:text-amber-400">
                  ${(parseFloat(price) / (result.attributes?.category === "outerwear" ? 15 : result.attributes?.category === "bottom" ? 35 : result.attributes?.category === "dress" ? 10 : 30)).toFixed(2)} / wear
                </p>
                <p className="text-[10px] text-muted-foreground">Economic amortization index</p>
              </div>
            </div>
          )}

          {/* 3 Component Results Grid (Vision, Try-On, Duplicate) */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-6">
            {/* 1. Garment Attributes Summary Card */}
            <Card className="flex flex-col border shadow-sm bg-card">
              <CardHeader className="pb-3 border-b bg-amber-600/5">
                <CardTitle className="flex items-center gap-2 text-sm font-bold text-amber-900 dark:text-amber-200">
                  <Sparkles className="h-4 w-4 text-amber-700 dark:text-amber-400" />
                  Vision Agent Attributes
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 flex-1 space-y-3 text-xs">
                {result.attributes ? (
                  <div className="grid grid-cols-2 gap-2.5">
                    {Object.entries(result.attributes).map(([key, val]) => (
                      <div key={key} className="rounded-xl bg-muted/40 p-2.5 border">
                        <span className="block text-[10px] uppercase font-bold text-muted-foreground">
                          {key}
                        </span>
                        <span className="font-semibold text-foreground capitalize mt-0.5 block">
                          {val || "Unknown"}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-xl bg-amber-500/10 p-3 text-amber-700 dark:text-amber-300 text-xs font-medium">
                    Attributes extraction skipped: {result.errors?.attributes || "Unavailable"}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* 2. Virtual Try-On & Fit Signal Card */}
            <Card className="flex flex-col border shadow-sm bg-card">
              <CardHeader className="pb-3 border-b bg-neutral-900/5 dark:bg-white/5">
                <CardTitle className="flex items-center gap-2 text-sm font-bold text-foreground">
                  <UserCheck className="h-4 w-4 text-amber-700 dark:text-amber-400" />
                  Virtual Try-On & Fit Signal
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 flex-1 space-y-3.5 text-xs">
                {result.tryon ? (
                  <div className="space-y-3">
                    {result.tryon.render_url && !result.tryon.tryon_degraded && !result.tryon.render_url.includes("placehold.co") ? (
                      <div className="relative aspect-video w-full overflow-hidden rounded-xl border bg-muted/30 shadow-sm flex items-center justify-center">
                        <img
                          src={result.tryon.render_url}
                          alt="Try-on render"
                          className="h-full w-full object-cover"
                        />
                      </div>
                    ) : (
                      <div className="p-4 rounded-xl border-2 border-dashed border-amber-600/30 bg-amber-600/5 flex flex-col items-center justify-center text-center gap-2">
                        <div className="flex h-12 w-12 items-center justify-center rounded-2xl bg-amber-600/15 text-amber-800 dark:text-amber-300">
                          <UserCheck className="h-6 w-6" />
                        </div>
                        <div>
                          <p className="font-bold text-foreground text-xs">Virtual Fit & Drape Analyzed</p>
                          <p className="text-[11px] text-muted-foreground mt-0.5">Physical silhouette & body drape mapped</p>
                        </div>
                      </div>
                    )}

                    <div className="flex flex-wrap gap-2">
                      {result.tryon.fit_tightness && (
                        <Badge variant="outline" className="text-[11px] capitalize font-bold bg-amber-600/10 text-amber-800 dark:text-amber-300 border-amber-600/20 px-2.5 py-0.5">
                          Tightness: {result.tryon.fit_tightness}
                        </Badge>
                      )}
                      {result.tryon.silhouette && (
                        <Badge variant="outline" className="text-[11px] capitalize font-bold bg-neutral-200/60 dark:bg-neutral-800/60 text-foreground border-border px-2.5 py-0.5">
                          Silhouette: {result.tryon.silhouette}
                        </Badge>
                      )}
                    </div>
                    {result.tryon.notes && (
                      <p className="text-muted-foreground text-xs bg-muted/40 p-2.5 rounded-xl border leading-relaxed font-normal">
                        {result.tryon.notes}
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="rounded-xl bg-amber-500/10 p-3 text-amber-600 dark:text-amber-400 space-y-1">
                    <div className="flex items-center gap-1.5 font-bold">
                      <AlertTriangle className="h-4 w-4 shrink-0" />
                      Try-On Skipped
                    </div>
                    <p className="text-[11px] leading-relaxed">
                      {result.errors?.tryon || "Model photo not set."}
                    </p>
                  </div>
                )}
              </CardContent>
            </Card>

            {/* 3. Duplicate Search Card */}
            <Card className="flex flex-col border shadow-sm bg-card">
              <CardHeader className="pb-3 border-b bg-amber-500/5">
                <CardTitle className="flex items-center gap-2 text-sm font-bold text-amber-700 dark:text-amber-300">
                  <Layers className="h-4 w-4 text-amber-500" />
                  Wardrobe Duplicate Search
                </CardTitle>
              </CardHeader>
              <CardContent className="p-4 flex-1">
                {result.errors?.duplicate ? (
                  <div className="rounded-xl bg-amber-500/10 p-3 text-amber-600 text-xs">
                    Duplicate check skipped: {result.errors.duplicate}
                  </div>
                ) : (
                  <NearDuplicateCard
                    match={result.duplicate}
                    hasDuplicate={!!result.duplicate}
                  />
                )}
              </CardContent>
            </Card>
          </div>

          {/* Decision Engine Verdict & Recharts 6-Axis Radar Card */}
          <div className="pt-2">
            <VerdictCard
              candidateId={result.candidate_item_id}
              initialData={result.candidate_item_id === 101 ? SAMPLE_BUY_SCORE_DEMO : undefined}
            />
          </div>
        </div>
      )}
    </div>
  );
}
