import type { CandidateEvaluationResult } from "@/lib/api";

const STORAGE_KEY = "verdict_candidate_evaluation_v1";

export interface SavedEvaluationSession {
  result: CandidateEvaluationResult;
  price: string;
  savedAt: string;
}

export function loadEvaluationSession(): SavedEvaluationSession | null {
  if (typeof window === "undefined") return null;
  try {
    const raw = window.localStorage.getItem(STORAGE_KEY);
    if (!raw) return null;
    const parsed = JSON.parse(raw) as SavedEvaluationSession;
    return parsed?.result?.candidate_item_id ? parsed : null;
  } catch {
    return null;
  }
}

export function saveEvaluationSession(result: CandidateEvaluationResult, price: string): void {
  if (typeof window === "undefined") return;
  window.localStorage.setItem(
    STORAGE_KEY,
    JSON.stringify({ result, price, savedAt: new Date().toISOString() }),
  );
}

export function clearEvaluationSession(): void {
  if (typeof window === "undefined") return;
  window.localStorage.removeItem(STORAGE_KEY);
}
