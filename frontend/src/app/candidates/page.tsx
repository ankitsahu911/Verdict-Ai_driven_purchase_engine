"use client";

import { ProtectedRoute } from "@/components/ProtectedRoute";
import { CandidateEvaluator } from "@/components/CandidateEvaluator";

export default function CandidateEvaluationPage() {
  return (
    <ProtectedRoute>
      <main className="min-h-screen bg-background">
        <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur">
          <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
            <h1 className="text-lg font-semibold">Evaluate Candidate Purchase Item</h1>
            <div className="flex items-center gap-4">
              <a href="/wardrobe" className="text-sm text-muted-foreground hover:text-foreground">
                Wardrobe
              </a>
              <a href="/dashboard" className="text-sm text-muted-foreground hover:text-foreground">
                Dashboard
              </a>
            </div>
          </div>
        </header>

        <div className="mx-auto max-w-6xl px-4 py-8">
          <CandidateEvaluator />
        </div>
      </main>
    </ProtectedRoute>
  );
}
