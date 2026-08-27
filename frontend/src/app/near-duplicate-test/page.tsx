"use client";

import { useEffect, useState } from "react";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { NearDuplicateCard } from "@/components/NearDuplicateCard";
import { Button } from "@/components/ui/button";
import { Input } from "@/components/ui/input";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import {
  type WardrobeItemData,
  type NearDuplicateResponse,
  fetchWardrobe,
  checkNearDuplicate,
} from "@/lib/api";

export default function NearDuplicateTestPage() {
  return (
    <ProtectedRoute>
      <NearDuplicateTestContent />
    </ProtectedRoute>
  );
}

function NearDuplicateTestContent() {
  const [items, setItems] = useState<WardrobeItemData[]>([]);
  const [loadingWardrobe, setLoadingWardrobe] = useState(true);
  const [selectedItemId, setSelectedItemId] = useState<number | null>(null);
  const [customImageUrl, setCustomImageUrl] = useState("");
  const [checking, setChecking] = useState(false);
  const [result, setResult] = useState<NearDuplicateResponse | null>(null);
  const [error, setError] = useState("");

  useEffect(() => {
    fetchWardrobe()
      .then((data) => setItems(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoadingWardrobe(false));
  }, []);

  async function handleCheckItem(itemId: number) {
    setSelectedItemId(itemId);
    setChecking(true);
    setError("");
    setResult(null);

    try {
      const res = await checkNearDuplicate({ item_id: itemId });
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to check near-duplicate");
    } finally {
      setChecking(false);
    }
  }

  async function handleCheckCustomUrl() {
    if (!customImageUrl.trim()) return;
    setSelectedItemId(null);
    setChecking(true);
    setError("");
    setResult(null);

    try {
      const res = await checkNearDuplicate({ image_url: customImageUrl.trim() });
      setResult(res);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Failed to check near-duplicate for URL");
    } finally {
      setChecking(false);
    }
  }

  return (
    <main className="min-h-screen bg-background">
      <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur">
        <div className="mx-auto flex h-14 max-w-5xl items-center justify-between px-4">
          <h1 className="text-lg font-semibold">Milestone 13: Near-Duplicate Detection Test</h1>
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

      <div className="mx-auto max-w-5xl px-4 py-8 space-y-6">
        <Card>
          <CardHeader>
            <CardTitle className="text-base font-medium">
              Check Candidate Image for Near-Duplicates
            </CardTitle>
          </CardHeader>
          <CardContent className="space-y-4">
            <div className="flex gap-2">
              <Input
                placeholder="Paste candidate item image URL (e.g. https://...)"
                value={customImageUrl}
                onChange={(e) => setCustomImageUrl(e.target.value)}
              />
              <Button onClick={handleCheckCustomUrl} disabled={checking || !customImageUrl.trim()}>
                {checking && !selectedItemId ? "Analyzing..." : "Check URL"}
              </Button>
            </div>
          </CardContent>
        </Card>

        {(result || checking) && (
          <div className="space-y-2">
            <h2 className="text-sm font-semibold uppercase tracking-wider text-muted-foreground">
              Detection Result
            </h2>
            <NearDuplicateCard
              match={result?.match ?? null}
              hasDuplicate={result?.has_duplicate ?? false}
              loading={checking}
            />
          </div>
        )}

        {error && (
          <p className="rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </p>
        )}

        <div className="space-y-3">
          <h2 className="text-base font-semibold">
            Select Existing Wardrobe Item to Test Nearest-Neighbor Lookup
          </h2>
          <p className="text-xs text-muted-foreground">
            Click any item below to search your ChromaDB collection for its nearest neighbor (excluding itself).
          </p>

          {loadingWardrobe && <p className="text-sm text-muted-foreground">Loading wardrobe...</p>}

          {!loadingWardrobe && items.length === 0 && (
            <p className="text-sm text-muted-foreground">No wardrobe items uploaded yet.</p>
          )}

          <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 md:grid-cols-4">
            {items.map((item) => (
              <Card
                key={item.id}
                onClick={() => handleCheckItem(item.id)}
                className={`cursor-pointer overflow-hidden transition-all hover:ring-2 hover:ring-primary ${
                  selectedItemId === item.id ? "ring-2 ring-primary" : ""
                }`}
              >
                <div className="relative aspect-square w-full bg-muted">
                  <img
                    src={item.cloudinary_url}
                    alt="Wardrobe item"
                    className="h-full w-full object-cover"
                  />
                </div>
                <CardContent className="p-2 text-center">
                  <p className="text-xs font-mono">Item #{item.id}</p>
                  <p className="text-[11px] text-muted-foreground capitalize">
                    {item.attributes?.category || "Uncategorized"}
                  </p>
                </CardContent>
              </Card>
            ))}
          </div>
        </div>
      </div>
    </main>
  );
}
