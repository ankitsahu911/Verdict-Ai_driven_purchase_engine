"use client";

import { CandidateEvaluator } from "@/components/CandidateEvaluator";
import { NavigationHeader } from "@/components/NavigationHeader";
import { Shirt } from "lucide-react";

export default function CandidateEvaluationPage() {
  return (
    <main className="min-h-screen bg-background pb-16">
      <NavigationHeader currentSubtitle="Candidate Evaluation" badgeText="Orchestrator" />

      <div className="w-full px-4 sm:px-6 lg:px-8 xl:px-10 py-6 sm:py-8 space-y-8">
        <div className="border-b pb-6">
          <div className="flex items-center gap-2 text-neutral-600 dark:text-neutral-400 font-bold text-xs uppercase tracking-[0.2em] mb-2">
            <Shirt className="h-4 w-4 text-neutral-800 dark:text-neutral-200" />
            <span>Multi-Agent Purchase Intake</span>
          </div>
          <h1 className="font-serif text-3xl sm:text-5xl font-normal tracking-tight text-foreground leading-tight">
            Candidate Garment Evaluator
          </h1>
          <p className="text-sm sm:text-base text-muted-foreground mt-2 max-w-3xl leading-relaxed">
            Upload a potential purchase to automatically extract attributes, generate virtual try-on fit analysis, detect wardrobe duplicates, and synthesize a buy verdict.
          </p>
        </div>

        <CandidateEvaluator />
      </div>
    </main>
  );
}
