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
  if (token) {
    headers["Authorization"] = `Bearer ${token}`;
  }
  const res = await fetch(`${API_URL}${path}`, { ...options, headers });
  if (!res.ok) {
    throw new Error(`API error: ${res.status}`);
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
        reject(new Error(`Upload failed (HTTP ${xhr.status})`));
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
}

export interface WardrobeItemData {
  id: number;
  cloudinary_url: string;
  uploaded_at: string;
  attributes: GarmentAttributesData | null;
}

export async function fetchWardrobe(): Promise<WardrobeItemData[]> {
  return apiFetch("/api/wardrobe");
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
}

export interface CandidateEvaluationResult {
  candidate_item_id: number;
  cloudinary_url: string;
  attributes: GarmentAttributesData | null;
  tryon: CandidateTryOnData | null;
  duplicate: NearDuplicateMatch | null;
  errors: Record<string, string> | null;
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

export interface BuyScoreResultData {
  candidate_id: number;
  verdict: "buy" | "consider" | "skip" | string;
  overall_score: number;
  headline_reason: string;
  axes: AxisScoreData[];
  weights_used: Record<string, number>;
  decision_log_id?: number | null;
  created_at: string;
}

export async function fetchCandidateBuyScore(candidateId: number): Promise<BuyScoreResultData> {
  return apiFetch(`/api/candidates/${candidateId}/buy-score`);
}