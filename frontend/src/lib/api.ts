const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export async function getAuthToken(): Promise<string | null> {
  const { auth } = await import("./firebase");
  if (!auth) return null;
  const user = auth.currentUser;
  if (!user) return null;
  return user.getIdToken();
}

export async function apiFetch(path: string, options: RequestInit = {}) {
  const token = await getAuthToken();
  const headers: Record<string, string> = {
    "Content-Type": "application/json",
    ...(options.headers as Record<string, string>),
  };
  
  const isDemo = typeof window !== "undefined" && localStorage.getItem("verdict_demo_token") === "true";
  if (isDemo) {
    headers["X-Verdict-User"] = "demo";
    headers["Authorization"] = "Bearer demo-token";
  } else if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }

  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    let detail = "";
    try {
      const errData = await res.json();
      if (errData && typeof errData === "object" && errData.detail) {
        detail = typeof errData.detail === "string" ? errData.detail : JSON.stringify(errData.detail);
      }
    } catch {
      // Ignore JSON parse error
    }
    throw new Error(detail || `API error: ${res.status}`);
  }
  return res.json();
}

export interface UploadedWardrobeItem {
  id: number;
  filename: string;
  url: string;
  public_id: string;
}

export interface UploadFailure {
  filename: string;
  error: string;
}

export interface UploadResponse {
  uploaded: UploadedWardrobeItem[];
  failed: UploadFailure[];
}

export function uploadWardrobePhoto(
  file: File,
  token: string,
  onProgress?: (percent: number) => void,
): Promise<UploadResponse> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}/api/wardrobe/upload`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as UploadResponse);
        } catch {
          reject(new Error("Invalid server response"));
        }
      } else {
        let errorMsg = `Upload failed (HTTP ${xhr.status})`;
        try {
          const errBody = JSON.parse(xhr.responseText);
          if (errBody?.detail) {
            errorMsg = typeof errBody.detail === "string" ? errBody.detail : JSON.stringify(errBody.detail);
          }
        } catch {
          // ignore
        }
        reject(new Error(errorMsg));
      }
    };

    xhr.onerror = () => reject(new Error("Network error during upload"));
    xhr.onabort = () => reject(new Error("Upload aborted"));

    xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    const form = new FormData();
    form.append("files", file, file.name);
    xhr.send(form);
  });
}

export interface GarmentAttributesData {
  category: string | null;
  color: string | null;
  pattern: string | null;
  style: string | null;
  season: string | null;
  material: string | null;
  extraction_source: string | null;
  provider_used?: string | null;
}

export interface WardrobeItemData {
  id: number;
  cloudinary_url: string;
  uploaded_at: string;
  attributes: GarmentAttributesData | null;
}

export async function fetchWardrobe(limit = 100): Promise<WardrobeItemData[]> {
  const res = await apiFetch(`/api/wardrobe?limit=${limit}`);
  if (Array.isArray(res)) return res;
  if (res && Array.isArray(res.items)) return res.items;
  return [];
}

export async function patchAttributes(
  itemId: number,
  attrs: Partial<GarmentAttributesData>,
): Promise<{ item_id: number; attributes: GarmentAttributesData }> {
  return apiFetch(`/api/wardrobe/${itemId}/attributes`, {
    method: "PATCH",
    body: JSON.stringify(attrs),
  });
}

export interface NearDuplicateMatch {
  wardrobe_item_id: number;
  cloudinary_url: string;
  similarity_percentage: number;
  distance: number;
  category: string;
  message: string;
}

export interface NearDuplicateResponse {
  has_duplicate: boolean;
  match: NearDuplicateMatch | null;
}

export async function checkNearDuplicate(
  req: { item_id?: number; image_url?: string },
): Promise<NearDuplicateResponse> {
  return apiFetch("/api/wardrobe/near-duplicate", {
    method: "POST",
    body: JSON.stringify(req),
  });
}

export interface CandidateTryOnData {
  render_url: string;
  fit_tightness: string | null;
  silhouette: string | null;
  notes: string | null;
  cached?: boolean;
  tryon_degraded?: boolean;
}

export interface CandidateEvaluationTimings {
  total_ms: number;
  vision_agent_ms: number;
  tryon_agent_ms: number;
  embedding_agent_ms: number;
  duplicate_detection_ms: number;
  target_ms: number;
  meets_target: boolean;
}

export interface CandidateEvaluationResult {
  candidate_item_id: number;
  cloudinary_url: string;
  attributes: GarmentAttributesData | null;
  tryon: CandidateTryOnData | null;
  duplicate: NearDuplicateMatch | null;
  errors: Record<string, string> | null;
  timings?: CandidateEvaluationTimings | null;
}

export function evaluateCandidate(
  file: File,
  token: string,
  onProgress?: (percent: number) => void,
): Promise<CandidateEvaluationResult> {
  return new Promise((resolve, reject) => {
    const xhr = new XMLHttpRequest();
    xhr.open("POST", `${API_URL}/api/candidates`);

    xhr.upload.onprogress = (event) => {
      if (event.lengthComputable && onProgress) {
        onProgress(Math.round((event.loaded / event.total) * 100));
      }
    };

    xhr.onload = () => {
      if (xhr.status >= 200 && xhr.status < 300) {
        try {
          resolve(JSON.parse(xhr.responseText) as CandidateEvaluationResult);
        } catch {
          reject(new Error("Invalid server response"));
        }
      } else {
        try {
          const errBody = JSON.parse(xhr.responseText);
          reject(new Error(errBody.detail || `Evaluation failed (HTTP ${xhr.status})`));
        } catch {
          reject(new Error(`Evaluation failed (HTTP ${xhr.status})`));
        }
      }
    };

    xhr.onerror = () => reject(new Error("Network error during candidate evaluation"));
    xhr.onabort = () => reject(new Error("Evaluation upload aborted"));

    xhr.setRequestHeader("Authorization", `Bearer ${token}`);
    const form = new FormData();
    form.append("file", file, file.name);
    xhr.send(form);
  });
}

export interface OutfitMatchItem {
  wardrobe_item_id: number;
  cloudinary_url: string;
  attributes: GarmentAttributesData | null;
  matched_because: string[];
}

export interface OutfitMatchesResponse {
  candidate_id: number;
  candidate_attributes: Record<string, string | null>;
  total_matches: number;
  matches: OutfitMatchItem[];
}

export async function fetchOutfitMatches(candidateId: number): Promise<OutfitMatchesResponse> {
  return apiFetch(`/api/candidates/${candidateId}/outfit-matches`);
}

export interface OutfitCombinationItem {
  wardrobe_item_id: number;
  cloudinary_url: string;
  attributes: GarmentAttributesData;
}

export interface OutfitCombination {
  outfit_id: string;
  total_score: number;
  reason_summary: string;
  candidate: OutfitCombinationItem;
  items: OutfitCombinationItem[];
  matched_rules: string[];
}

export interface OutfitCombinationsResponse {
  candidate_id: number;
  total_combinations_found: number;
  combinations: OutfitCombination[];
}

export async function fetchOutfitCombinations(candidateId: number): Promise<OutfitCombinationsResponse> {
  return apiFetch(`/api/candidates/${candidateId}/outfit-combinations`);
}

export interface ReturnRiskData {
  score: number;
  baseline_risk: number;
  fit_adjustment: number;
  fit_tightness: string;
  reasoning: string;
}

export interface CandidateEconomicsData {
  candidate_id: number;
  price: number;
  cost_per_wear: number;
  baseline_wears_used: number;
  category: string;
  return_risk: ReturnRiskData | null;
}

export async function updateCandidatePrice(
  candidateId: number,
  price: number,
): Promise<{ candidate_id: number; price: number }> {
  return apiFetch(`/api/candidates/${candidateId}/price`, {
    method: "PATCH",
    body: JSON.stringify({ price }),
  });
}

export async function fetchCandidateEconomics(candidateId: number): Promise<CandidateEconomicsData> {
  return apiFetch(`/api/candidates/${candidateId}/economics`);
}

export type DecisionAxis =
  | "versatility"
  | "redundancy"
  | "seasonal_relevance"
  | "budget_impact"
  | "style_alignment"
  | "occasion_coverage";

export interface AxisScoreData {
  axis: DecisionAxis;
  score: number;
  reason: string;
  source_agent: string;
  raw_evidence?: Record<string, unknown> | null;
}

export interface CandidateDecisionPayloadData {
  candidate_id: number;
  scores: Record<DecisionAxis, AxisScoreData>;
  overall_score?: number | null;
}

export interface CandidateAxesResponse {
  candidate_id: number;
  total_axes: number;
  axes: AxisScoreData[];
}

export async function fetchCandidateAxes(candidateId: number): Promise<CandidateAxesResponse> {
  return apiFetch(`/api/candidates/${candidateId}/axes`);
}

export interface ConfidenceResultData {
  level: "high" | "medium" | "low" | string;
  reasoning: string;
  signals?: Record<string, any> | null;
}

export interface DecisionSummaryMetricsData {
  versatility: number;
  versatility_outfits_count: number;
  duplicate_risk: number;
  duplicate_risk_label: string;
  seasonality: number;
  seasonality_label: string;
  cost_per_wear: number;
  cost_per_wear_formatted: string;
  sustainability_tier: "Lower impact" | "Higher impact" | "Unrated" | string;
  sustainability_reason: string;
  is_estimate: boolean;
}

export interface BuyScoreResultData {
  candidate_id: number;
  verdict: "buy" | "consider" | "skip" | string;
  overall_score: number;
  headline_reason: string;
  axes: AxisScoreData[];
  weights_used: Record<string, number>;
  decision_log_id?: number | null;
  confidence?: ConfidenceResultData | null;
  summary_panel?: DecisionSummaryMetricsData | null;
  tryon_degraded?: boolean;
  created_at: string;
}

export async function fetchCandidateBuyScore(candidateId: number): Promise<BuyScoreResultData> {
  return apiFetch(`/api/candidates/${candidateId}/buy-score`);
}

export interface CandidateItemData {
  id: number;
  cloudinary_url: string;
  price: number | null;
  fit_tightness?: string | null;
  silhouette?: string | null;
  tryon_render_url?: string | null;
  tryon_cached_model_photo_url?: string | null;
  tryon_degraded?: boolean;
  duplicate_similarity_pct?: number | null;
  uploaded_at: string;
  attributes: GarmentAttributesData | null;
}

export async function updateModelPhoto(
  modelPhotoUrl: string,
): Promise<{ user_id: number; model_photo_url: string }> {
  return apiFetch("/api/me/model-photo", {
    method: "PATCH",
    body: JSON.stringify({ model_photo_url: modelPhotoUrl }),
  });
}

export async function requestTryOn(
  itemId: number,
  options?: { user_photo_url?: string; garment_category?: string; force?: boolean },
): Promise<CandidateTryOnData & { cached: boolean }> {
  const query = options?.force ? "?force=true" : "";
  return apiFetch(`/api/tryon/${itemId}${query}`, {
    method: "POST",
    body: JSON.stringify({
      user_photo_url: options?.user_photo_url,
      garment_category: options?.garment_category,
    }),
  });
}

export async function fetchCandidates(): Promise<CandidateItemData[]> {
  return apiFetch("/api/candidates");
}

export interface SubsetRecordData {
  subset_id: string;
  size: number;
  item_ids: number[];
}

export interface EnumerateSubsetsResponseData {
  total_items: number;
  total_subsets: number;
  subsets: SubsetRecordData[];
}

export async function enumerateSubsets(itemIds: number[]): Promise<EnumerateSubsetsResponseData> {
  return apiFetch("/api/what-if/enumerate", {
    method: "POST",
    body: JSON.stringify({ item_ids: itemIds }),
  });
}

export interface ScoredSubsetData {
  subset_id: string;
  rank: number;
  size: number;
  item_ids: number[];
  verdict: "buy" | "consider" | "skip" | string;
  overall_score: number;
  headline_reason: string;
  axes: AxisScoreData[];
  total_price: number;
  confidence?: ConfidenceResultData | null;
  summary_panel?: DecisionSummaryMetricsData | null;
}

export interface ScoreSubsetsResponseData {
  total_items: number;
  total_subsets: number;
  top_recommendation: ScoredSubsetData;
  subsets: ScoredSubsetData[];
}

export async function scoreWhatIfSubsets(itemIds: number[]): Promise<ScoreSubsetsResponseData> {
  return apiFetch("/api/what-if/score", {
    method: "POST",
    body: JSON.stringify({ item_ids: itemIds }),
  });
}

export interface OpportunityCostCompareResponseData {
  candidate: BuyScoreResultData;
  alternative_bundle: ScoredSubsetData;
  candidate_versatility: number;
  alternative_bundle_versatility: number;
  versatility_delta: number;
  candidate_outfit_count: number;
  alternative_bundle_outfit_count: number;
  outfit_count_delta: number;
  candidate_name: string;
  alternative_names: string[];
}

export async function compareOpportunityCost(
  candidateItemId: number,
  alternativeItemIds: number[],
): Promise<OpportunityCostCompareResponseData> {
  return apiFetch("/api/opportunity-cost/compare", {
    method: "POST",
    body: JSON.stringify({
      candidate_item_id: candidateItemId,
      alternative_item_ids: alternativeItemIds,
    }),
  });
}

export interface RetrievedWardrobeItemData {
  id: number;
  category: string;
  color: string;
  style: string;
  pattern: string;
  season: string;
  material: string;
  thumbnail_url: string | null;
  similarity_score: number;
  distance: number;
}

export interface StylistChatResponseData {
  reply: string;
  retrieved_items: RetrievedWardrobeItemData[];
  provider_used: string;
  model_used: string;
  guardrail_triggered?: boolean;
}

export async function chatWithStylist(
  message: string,
  topK: number = 5,
): Promise<StylistChatResponseData> {
  return apiFetch("/api/stylist/chat", {
    method: "POST",
    body: JSON.stringify({
      message,
      top_k: topK,
    }),
  });
}