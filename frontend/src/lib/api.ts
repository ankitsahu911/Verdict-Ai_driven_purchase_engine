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

/**
 * Upload a single photo to /api/wardrobe/upload using XHR so we get
 * real per-file upload progress. Requires a Firebase ID token.
 */
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