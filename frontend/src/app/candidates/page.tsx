"use client";

import { CandidateEvaluator } from "@/components/CandidateEvaluator";
import { NavigationHeader } from "@/components/NavigationHeader";
import { Shirt } from "lucide-react";

export default function CandidateEvaluationPage() {
  return (
    <main className="min-h-screen bg-gradient-to-b from-background via-background to-muted/20 pb-16">
      <NavigationHeader currentSubtitle="Candidate Evaluation" badgeText="Orchestrator" />

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 sm:py-10 space-y-8">
        <div className="border-b pb-6">
          <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider mb-1.5">
            <Shirt className="h-4 w-4 text-primary" />
            <span>Multi-Agent Purchase Intake</span>
          </div>
          <h1 className="text-3xl sm:text-4xl font-extrabold tracking-tight text-foreground">
            Candidate Garment Evaluator
          </h1>
          <p className="text-sm sm:text-base text-muted-foreground mt-1.5 max-w-3xl">
            Upload a potential purchase to automatically extract attributes, generate virtual try-on fit analysis, detect wardrobe duplicates, and synthesize a buy verdict.
          </p>
        </div>

        <CandidateEvaluator />
      </div>
    </main>
  );
}
