"use client";

import { useCallback, useEffect, useState } from "react";
import { motion, AnimatePresence } from "framer-motion";
import { Pencil, Plus, UploadCloud } from "lucide-react";
import { PhotoUploader } from "@/components/PhotoUploader";
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
import { NavigationHeader } from "@/components/NavigationHeader";
import {
  fadeUpVariants,
  staggerContainerVariants,
  staggerItemVariants,
  DURATION_FAST,
} from "@/lib/animations";
import {
  type WardrobeItemData,
  type GarmentAttributesData,
  fetchWardrobe,
  patchAttributes,
  updateWardrobePrice,
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
  const [editPrice, setEditPrice] = useState<string>("");
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
  const [isUploadOpen, setIsUploadOpen] = useState(false);

  const load = useCallback(() => {
    fetchWardrobe()
      .then((data) => setItems(Array.isArray(data) ? data : (data as any)?.items || []))
      .catch((err) => setError(err.message))
      .finally(() => setLoading(false));
  }, []);

  useEffect(() => {
    load();
  }, [load]);

  function openEdit(item: WardrobeItemData) {
    const a = item.attributes;
    setEditPrice(item.price ? String(item.price) : "");
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

      let updatedPrice = editingItem.price;
      if (editPrice !== "") {
        const parsedP = parseFloat(editPrice);
        if (!isNaN(parsedP)) {
          const priceRes = await updateWardrobePrice(editingItem.id, parsedP);
          updatedPrice = priceRes.price;
        }
      }

      setItems((prev) =>
        prev.map((it) =>
          it.id === editingItem.id
            ? { ...it, attributes: result.attributes, price: updatedPrice }
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
    <main className="min-h-screen bg-background pb-16">
      <NavigationHeader currentSubtitle="Wardrobe Grid" badgeText="Curated Closet" />

      <div className="w-full px-4 sm:px-6 lg:px-8 xl:px-10 py-6 sm:py-8">
        <motion.div
          initial="hidden"
          animate="visible"
          variants={fadeUpVariants}
          className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 mb-6 pb-5 border-b"
        >
          <div>
            <h1 className="font-serif text-3xl sm:text-5xl font-normal tracking-tight text-foreground">
              Wardrobe Collection
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground mt-1">
              Curated closet • Fully tagged and embedded in ChromaDB for instant vector matching
            </p>
          </div>
          <div className="flex items-center gap-3 shrink-0">
            <Badge variant="buy" className="text-xs font-bold px-3 py-1 shadow-xs rounded-lg">
              Pre-Verified ({items.length} items)
            </Badge>
            <Button
              onClick={() => setIsUploadOpen(true)}
              size="default"
              className="h-11 px-6 gap-2 font-bold shadow-md bg-neutral-900 text-white hover:bg-black dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-100 rounded-xl cursor-pointer"
            >
              <Plus className="h-4.5 w-4.5" />
              Add to Wardrobe
            </Button>
          </div>
        </motion.div>

        {error && (
          <div className="mb-6 rounded-2xl bg-destructive/10 p-4 text-sm text-destructive border border-destructive/20 font-medium">
            {error}
          </div>
        )}

        {loading && <SkeletonGrid />}

        {!loading && items.length === 0 && (
          <div className="flex flex-col items-center justify-center rounded-2xl border border-dashed py-24 text-center bg-muted/10">
            <p className="text-lg font-bold text-muted-foreground">
              No items yet
            </p>
            <p className="mt-1 text-sm text-muted-foreground/80 max-w-md">
              Upload some wardrobe photos from the dashboard to get started with outfit evaluation.
            </p>
            <a href="/dashboard" className="mt-4">
              <Button variant="outline" size="sm" className="font-semibold rounded-xl">
                Go to Dashboard
              </Button>
            </a>
          </div>
        )}

        {!loading && items.length > 0 && (
          <motion.div
            initial="hidden"
            animate="visible"
            variants={staggerContainerVariants}
            className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-7 3xl:grid-cols-8 gap-4 sm:gap-5"
          >
            <AnimatePresence mode="popLayout">
              {items.map((item) => (
                <motion.div
                  key={item.id}
                  layout
                  variants={staggerItemVariants}
                  whileHover={{ y: -3, transition: { duration: DURATION_FAST } }}
                >
                  <Card
                    className={`group relative overflow-hidden rounded-2xl border border-border/80 dark:border-[#342646] shadow-sm transition-all hover:shadow-xl hover:border-primary/50 glass-panel ${
                      flashId === item.id
                        ? "ring-2 ring-amber-600/60"
                        : ""
                    }`}
                  >
                    <motion.div
                      animate={
                        flashId === item.id
                          ? { backgroundColor: ["rgba(173,126,74,0.15)", "transparent"] }
                          : {}
                      }
                      transition={{ duration: 1.2 }}
                      className="absolute inset-0 -z-10"
                    />
                    <div className="relative aspect-square w-full overflow-hidden bg-muted/30">
                      <img
                        src={item.cloudinary_url}
                        alt="Wardrobe item"
                        className="h-full w-full object-cover object-center transition-transform duration-500 group-hover:scale-108"
                        loading="lazy"
                      />
                      <button
                        onClick={() => openEdit(item)}
                        className="absolute right-2.5 top-2.5 rounded-full bg-background/85 p-2 opacity-0 shadow-md backdrop-blur transition-opacity group-hover:opacity-100"
                        aria-label="Edit attributes"
                      >
                        <Pencil className="h-3.5 w-3.5 text-foreground" />
                      </button>
                    </div>
                    <CardContent className="p-3 sm:p-4 space-y-2">
                      {item.price && (
                        <div className="flex items-center justify-between pb-1.5 border-b border-border/40">
                          <span className="text-[10px] uppercase font-bold text-muted-foreground tracking-wider">Cost</span>
                          <span className="font-mono font-bold text-xs text-amber-800 dark:text-amber-300 bg-amber-500/10 px-2 py-0.5 rounded-md border border-amber-600/30">
                            ${item.price.toFixed(2)}
                          </span>
                        </div>
                      )}
                      <div className="flex flex-wrap gap-1">
                        {ATTRIBUTE_FIELDS.map((key) => {
                          const val = item.attributes?.[key];
                          if (!val) return null;
                          return (
                            <Badge key={key} variant="secondary" className="text-[10.5px] font-medium px-2 py-0.5 rounded-md bg-secondary/80 text-foreground">
                              {val}
                            </Badge>
                          );
                        })}
                        {item.attributes?.extraction_source === "ai" && (
                          <Badge variant="outline" className="text-[9.5px] px-1.5 py-0 rounded-md">
                            AI
                          </Badge>
                        )}
                        {item.attributes?.extraction_source === "manual_override" && (
                          <Badge variant="outline" className="text-[9.5px] px-1.5 py-0 rounded-md">
                            Manual
                          </Badge>
                        )}
                      </div>
                    </CardContent>
                  </Card>
                </motion.div>
              ))}
            </AnimatePresence>
          </motion.div>
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

          {/* Garment Price Input */}
          <div className="p-3 rounded-xl border border-border/80 bg-muted/20 space-y-1">
            <label className="text-xs font-bold text-foreground">
              Garment Cost / Price ($)
            </label>
            <Input
              type="number"
              min="0"
              step="0.01"
              value={editPrice}
              onChange={(e) => setEditPrice(e.target.value)}
              placeholder="e.g. 75.00"
            />
            <p className="text-[10px] text-muted-foreground">Used directly to calculate live Cost-Per-Wear.</p>
          </div>

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

      {/* Upload Garments Dialog */}
      <Dialog open={isUploadOpen} onOpenChange={setIsUploadOpen}>
        <DialogContent className="max-w-2xl bg-card">
          <DialogHeader>
            <DialogTitle className="flex items-center gap-2 text-lg font-bold">
              <UploadCloud className="h-5 w-5 text-primary" />
              Add Clothes to Your Wardrobe
            </DialogTitle>
          </DialogHeader>
          <div className="mt-2">
            <PhotoUploader
              onUploadComplete={() => {
                load();
                setTimeout(() => setIsUploadOpen(false), 1200);
              }}
            />
          </div>
        </DialogContent>
      </Dialog>
    </main>
  );
}

function SkeletonGrid() {
  return (
    <div className="grid grid-cols-2 sm:grid-cols-3 md:grid-cols-4 lg:grid-cols-5 xl:grid-cols-6 2xl:grid-cols-7 3xl:grid-cols-8 gap-4 sm:gap-5">
      {Array.from({ length: 12 }).map((_, i) => (
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
