"use client";

import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Pencil } from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Card, CardContent } from "@/components/ui/card";
import {
  Dialog,
  DialogContent,
  DialogHeader,
  DialogTitle,
  DialogFooter,
} from "@/components/ui/dialog";
import { Input } from "@/components/ui/input";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import {
  type WardrobeItemData,
  type GarmentAttributesData,
  fetchWardrobe,
  patchAttributes,
} from "@/lib/api";

const ATTRIBUTE_FIELDS: (keyof GarmentAttributesData)[] = [
  "category",
  "color",
  "pattern",
  "style",
  "season",
  "material",
];

const FIELD_LABELS: Record<string, string> = {
  category: "Category",
  color: "Color",
  pattern: "Pattern",
  style: "Style",
  season: "Season",
  material: "Material",
};

export default function WardrobePage() {
  return (
    <ProtectedRoute>
      <WardrobeContent />
    </ProtectedRoute>
  );
}

function WardrobeContent() {
  const [items, setItems] = useState<WardrobeItemData[]>([]);
  const [loading, setLoading] = useState(true);
  const [error, setError] = useState("");
  const [editingItem, setEditingItem] = useState<WardrobeItemData | null>(null);
  const [editForm, setEditForm] = useState<GarmentAttributesData>({
    category: "",
    color: "",
    pattern: "",
    style: "",
    season: "",
    material: "",
    extraction_source: null,
  });
  const [saving, setSaving] = useState(false);
  const [flashId, setFlashId] = useState<number | null>(null);

  const load = useCallback(() => {
    fetchWardrobe()
      .then((data) => setItems(data))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function openEdit(item: WardrobeItemData) {
    const a = item.attributes;
    setEditForm({
      category: a?.category ?? "",
      color: a?.color ?? "",
      pattern: a?.pattern ?? "",
      style: a?.style ?? "",
      season: a?.season ?? "",
      material: a?.material ?? "",
      extraction_source: a?.extraction_source ?? null,
    });
    setEditingItem(item);
  }

  async function handleSave() {
    if (!editingItem) return;
    setSaving(true);
    try {
      const payload: Record<string, string> = {};
      for (const key of ATTRIBUTE_FIELDS) {
        const val = editForm[key];
        if (val !== undefined && val !== null) {
          payload[key] = val;
        }
      }
      const result = await patchAttributes(editingItem.id, payload);

      setItems((prev) =>
        prev.map((it) =>
          it.id === editingItem.id
            ? { ...it, attributes: result.attributes }
            : it,
        ),
      );

      setFlashId(editingItem.id);
      setTimeout(() => setFlashId(null), 1200);
      setEditingItem(null);
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Save failed");
    } finally {
      setSaving(false);
    }
  }

  return (
    <main className="min-h-screen bg-background">
      <header className="sticky top-0 z-10 border-b bg-background/95 backdrop-blur supports-[backdrop-filter]:bg-background/60">
        <div className="mx-auto flex h-14 max-w-6xl items-center justify-between px-4">
          <h1 className="text-lg font-semibold">Wardrobe</h1>
          <a href="/dashboard" className="text-sm text-muted-foreground hover:text-foreground">
            &larr; Dashboard
          </a>
        </div>
      </header>

      <div className="mx-auto max-w-6xl px-4 py-8">
        {error && (
          <p className="mb-4 rounded-md bg-destructive/10 p-3 text-sm text-destructive">
            {error}
          </p>
        )}

        {loading && <SkeletonGrid />}

        {!loading && items.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-lg border border-dashed py-24 text-center">
            <p className="text-lg font-medium text-muted-foreground">
              No items yet
            </p>
            <p className="mt-1 text-sm text-muted-foreground/80">
              Upload some wardrobe photos from the dashboard to get started.
            </p>
            <a href="/dashboard" className="mt-4">
              <Button variant="outline" size="sm">
                Go to Dashboard
              </Button>
            </a>
          </div>
        )}

        {!loading && items.length > 0 && (
          <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
            <AnimatePresence mode="popLayout">
              {items.map((item) => (
                <motion.div
                  key={item.id}
                  layout
                  initial={{ opacity: 0, scale: 0.95 }}
                  animate={{ opacity: 1, scale: 1 }}
                  transition={{ duration: 0.2 }}
                >
                  <Card
                    className={`group relative overflow-hidden transition-shadow hover:shadow-md ${
                      flashId === item.id
                        ? "ring-2 ring-green-500/60"
                        : ""
                    }`}
                  >
                    <motion.div
                      animate={
                        flashId === item.id
                          ? { backgroundColor: ["rgba(34,197,94,0.08)", "transparent"] }
                          : {}
                      }
                      transition={{ duration: 1.2 }}
                      className="absolute inset-0 -z-10"
                    />
                    <div className="relative aspect-square w-full overflow-hidden bg-muted">
                      <img
                        src={item.cloudinary_url}
                        alt="Wardrobe item"
                        className="h-full w-full object-cover"
                      />
                      <button
                        onClick={() => openEdit(item)}
                        className="absolute right-2 top-2 rounded-full bg-background/80 p-1.5 opacity-0 shadow-sm backdrop-blur transition-opacity group-hover:opacity-100"
                        aria-label="Edit attributes"
                      >
                        <Pencil className="h-4 w-4" />
                      </button>
                    </div>
                    <CardContent className="p-4">
                      <div className="flex flex-wrap gap-1.5">
                        {ATTRIBUTE_FIELDS.map((key) => {
                          const val = item.attributes?.[key];
                          if (!val) return null;
                          return (
                            <Badge key={key} variant="secondary" className="text-[11px]">
                              {val}
                            </Badge>
                          );
                        })}
                        {item.attributes?.extraction_source === "ai" && (
                          <Badge variant="outline" className="text-[11px]">
                            AI
                          </Badge>
                        )}
                        {item.attributes?.extraction_source === "manual_override" && (
                          <Badge variant="outline" className="text-[11px]">
                            Manual
                          </Badge>
                        )}
                        {!item.attributes && (
                          <span className="text-xs text-muted-foreground">
                            Not analyzed
                          </span>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}
      </div>

      <Dialog
        open={!!editingItem}
        onOpenChange={(open) => {
          if (!open) setEditingItem(null);
        }}
      >
        <DialogContent className="sm:max-w-md">
          <DialogHeader>
            <DialogTitle>Edit Attributes</DialogTitle>
          </DialogHeader>

          {editingItem && (
            <div className="relative mb-2 aspect-video w-full overflow-hidden rounded-md bg-muted">
              <img
                src={editingItem.cloudinary_url}
                alt="Item preview"
                className="h-full w-full object-cover"
              />
            </div>
          )}

          <div className="grid grid-cols-2 gap-3">
            {ATTRIBUTE_FIELDS.map((key) => (
              <div key={key}>
                <label className="mb-1 block text-xs font-medium text-muted-foreground">
                  {FIELD_LABELS[key]}
                </label>
                <Input
                  value={editForm[key] ?? ""}
                  onChange={(e) =>
                    setEditForm((prev) => ({ ...prev, [key]: e.target.value }))
                  }
                  placeholder={FIELD_LABELS[key]}
                />
              </div>
            ))}
          </div>

          <DialogFooter>
            <Button
              variant="outline"
              onClick={() => setEditingItem(null)}
              disabled={saving}
            >
              Cancel
            </Button>
            <Button onClick={handleSave} disabled={saving}>
              {saving ? "Saving…" : "Save"}
            </Button>
          </DialogFooter>
        </DialogContent>
      </Dialog>
    </main>
  );
}

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-1 gap-4 sm:grid-cols-2 lg:grid-cols-3">
      {Array.from({ length: 6 }).map((_, i) => (
        <Card key={i} className="overflow-hidden">
          <div className="aspect-square w-full animate-pulse bg-muted" />
          <div className="flex gap-2 p-4">
            {Array.from({ length: 3 }).map((__, j) => (
              <div
                key={j}
                className="h-5 w-16 animate-pulse rounded bg-muted"
              />
            ))}
          </div>
        </Card>
      ))}
    </div>
  );
}
