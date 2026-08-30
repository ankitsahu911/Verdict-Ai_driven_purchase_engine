"use client";

import React, { useState } from "react";
import {
  Upload,
  Sparkles,
  Shirt,
  UserCheck,
  Layers,
  AlertTriangle,
  CheckCircle2,
  Loader2,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Progress } from "@/components/ui/progress";
import { NearDuplicateCard } from "@/components/NearDuplicateCard";
import { VerdictCard } from "@/components/VerdictCard";
import { getAuthToken, evaluateCandidate, type CandidateEvaluationResult } from "@/lib/api";

const STAGES = [
  { id: 1, label: "Uploading photo...", icon: Upload },
  { id: 2, label: "Analyzing garment attributes with Vision AI...", icon: Sparkles },
  { id: 3, label: "Generating virtual try-on & fit signals...", icon: UserCheck },
  { id: 4, label: "Checking wardrobe for near-duplicates...", icon: Layers },
];

export function CandidateEvaluator() {
  const [file, setFile] = useState<File | null>(null);
  const [previewUrl, setPreviewUrl] = useState<string | null>(null);
  const [loading, setLoading] = useState(false);
  const [currentStage, setCurrentStage] = useState<number>(1);
  const [result, setResult] = useState<CandidateEvaluationResult | null>(null);
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

  async function handleEvaluate() {
    if (!file) return;
    setLoading(true);
    setError(null);
    setResult(null);
    setCurrentStage(1);

    // Staged progress timer updates for UX during multi-step orchestration
    const timer1 = setTimeout(() => setCurrentStage(2), 1500);
    const timer2 = setTimeout(() => setCurrentStage(3), 4000);
    const timer3 = setTimeout(() => setCurrentStage(4), 8000);

    try {
      const token = await getAuthToken();
      if (!token) {
        throw new Error("Authentication token not found. Please log in.");
      }

      const res = await evaluateCandidate(file, token);
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
    <div className="space-y-6">
      {/* Upload & Action Card */}
      <Card className="border-primary/20 shadow-sm">
        <CardHeader className="pb-3">
          <CardTitle className="flex items-center gap-2 text-base font-semibold">
            <Shirt className="h-5 w-5 text-primary" />
            Add an Item to Evaluate
          </CardTitle>
        </CardHeader>
        <CardContent className="space-y-4">
          <div className="flex flex-col sm:flex-row items-center gap-4">
            <label className="flex-1 w-full flex items-center justify-center gap-3 border-2 border-dashed border-muted-foreground/30 hover:border-primary/50 rounded-lg p-4 cursor-pointer transition-colors bg-muted/20">
              <Upload className="h-5 w-5 text-muted-foreground" />
              <span className="text-sm font-medium text-muted-foreground">
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

            <Button
              onClick={handleEvaluate}
              disabled={!file || loading}
              className="w-full sm:w-auto px-6"
            >
              {loading ? (
                <>
                  <Loader2 className="mr-2 h-4 w-4 animate-spin" />
                  Evaluating...
                </>
              ) : (
                <>
                  <Sparkles className="mr-2 h-4 w-4" />
                  Evaluate Candidate
                </>
              )}
            </Button>
          </div>

          {/* Staged Loading State Indicator */}
          {loading && (
            <div className="space-y-3 pt-2">
              <div className="flex items-center justify-between text-xs font-semibold text-primary">
                <span>{STAGES[currentStage - 1].label}</span>
                <span>Stage {currentStage} of 4</span>
              </div>
              <Progress value={(currentStage / 4) * 100} className="h-2" />
              <div className="grid grid-cols-2 sm:grid-cols-4 gap-2 pt-1">
                {STAGES.map((s) => {
                  const Icon = s.icon;
                  const isActive = s.id === currentStage;
                  const isDone = s.id < currentStage;
                  return (
                    <div
                      key={s.id}
                      className={`flex items-center gap-2 rounded-md p-2 text-xs transition-colors ${
                        isActive
                          ? "bg-primary/10 font-semibold text-primary"
                          : isDone
                          ? "bg-muted text-muted-foreground line-through opacity-70"
                          : "bg-muted/30 text-muted-foreground/60"
                      }`}
                    >
                      <Icon className="h-3.5 w-3.5 shrink-0" />
                      <span className="truncate">{s.label.split("...")[0]}</span>
                    </div>
                  );
                })}
              </div>
            </div>
          )}

          {error && (
            <div className="flex items-center gap-2 rounded-md bg-destructive/10 p-3 text-xs text-destructive">
              <AlertTriangle className="h-4 w-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}
        </CardContent>
      </Card>

      {/* Orchestrated Single-Screen Evaluation Results */}
      {result && (
        <div className="space-y-6">
          {/* Header Banner */}
          <div className="flex flex-col sm:flex-row items-start sm:items-center justify-between gap-3 border-b pb-3">
            <div className="flex items-center gap-3">
              <img
                src={result.cloudinary_url}
                alt="Candidate photo"
                className="h-12 w-12 rounded-md object-cover border"
              />
              <div>
                <h2 className="text-lg font-bold text-foreground">Candidate Evaluation Results</h2>
                <p className="text-xs text-muted-foreground">
                  Item <code className="font-mono font-semibold">#{result.candidate_item_id}</code> evaluated across Vision, Try-On, Embedding, and Wardrobe search.
                </p>
              </div>
            </div>
          </div>

          {/* Milestone 24: Decision Engine Verdict & Recharts 6-Axis Radar Card */}
          <VerdictCard candidateId={result.candidate_item_id} />

          {/* 3 Component Results Grid (Vision, Try-On, Duplicate) */}
          <div className="grid grid-cols-1 md:grid-cols-3 gap-4">
            {/* 1. Garment Attributes Summary Card */}
            <Card className="flex flex-col">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                  <Sparkles className="h-4 w-4 text-purple-500" />
                  Garment Attributes
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1 space-y-3 text-xs">
                {result.attributes ? (
                  <div className="grid grid-cols-2 gap-2">
                    {Object.entries(result.attributes).map(([key, val]) => (
                      <div key={key} className="rounded-md bg-muted/40 p-2">
                        <span className="block text-[10px] uppercase font-semibold text-muted-foreground">
                          {key}
                        </span>
                        <span className="font-medium text-foreground capitalize">
                          {val || "Unknown"}
                        </span>
                      </div>
                    ))}
                  </div>
                ) : (
                  <div className="rounded-md bg-amber-500/10 p-3 text-amber-600 text-xs">
                    Attributes extraction skipped: {result.errors?.attributes || "Unavailable"}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* 2. Virtual Try-On & Fit Signal Card */}
            <Card className="flex flex-col">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                  <UserCheck className="h-4 w-4 text-blue-500" />
                  Virtual Try-On & Fit Signal
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1 space-y-3 text-xs">
                {result.tryon ? (
                  <div className="space-y-3">
                    <div className="relative aspect-video w-full overflow-hidden rounded-md border bg-muted">
                      <img
                        src={result.tryon.render_url}
                        alt="Try-on render"
                        className="h-full w-full object-cover"
                      />
                    </div>
                    <div className="flex gap-2">
                      {result.tryon.fit_tightness && (
                        <Badge variant="outline" className="text-[11px] capitalize">
                          Tightness: {result.tryon.fit_tightness}
                        </Badge>
                      )}
                      {result.tryon.silhouette && (
                        <Badge variant="outline" className="text-[11px] capitalize">
                          Silhouette: {result.tryon.silhouette}
                        </Badge>
                      )}
                    </div>
                    {result.tryon.notes && (
                      <p className="text-muted-foreground text-[11px] bg-muted/30 p-2 rounded">
                        {result.tryon.notes}
                      </p>
                    )}
                  </div>
                ) : (
                  <div className="rounded-md bg-amber-500/10 p-3 text-amber-600 dark:text-amber-400 space-y-1">
                    <div className="flex items-center gap-1.5 font-semibold">
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

            {/* 3. Near-Duplicate Match Card */}
            <Card className="flex flex-col">
              <CardHeader className="pb-2">
                <CardTitle className="flex items-center gap-2 text-sm font-semibold">
                  <Layers className="h-4 w-4 text-amber-500" />
                  Wardrobe Duplicate Search
                </CardTitle>
              </CardHeader>
              <CardContent className="flex-1">
                {result.errors?.duplicate ? (
                  <div className="rounded-md bg-amber-500/10 p-3 text-amber-600 text-xs">
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
        </div>
      )}
    </div>
  );
}
