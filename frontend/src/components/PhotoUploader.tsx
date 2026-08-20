"use client";

import {
  useCallback,
  useEffect,
  useMemo,
  useRef,
  useState,
} from "react";
import { AnimatePresence, motion } from "framer-motion";
import {
  AlertCircle,
  CheckCircle2,
  FileImage,
  Loader2,
  UploadCloud,
  X,
} from "lucide-react";

import { Button } from "@/components/ui/button";
import {
  Card,
  CardContent,
  CardDescription,
  CardHeader,
  CardTitle,
} from "@/components/ui/card";
import { Progress } from "@/components/ui/progress";
import { cn } from "@/lib/utils";
import {
  getAuthToken,
  uploadWardrobePhoto,
  type UploadedWardrobeItem,
} from "@/lib/api";

type Status = "pending" | "uploading" | "done" | "error";

interface UploadItem {
  id: string;
  file: File;
  preview: string;
  name: string;
  size: number;
  status: Status;
  progress: number;
  error?: string;
  result?: UploadedWardrobeItem;
}

const ACCEPTED_TYPES = ["image/jpeg", "image/png", "image/webp"];
const ACCEPTED_EXTENSIONS = [".jpg", ".jpeg", ".png", ".webp"];
const MAX_BYTES = 10 * 1024 * 1024;
const CONCURRENCY = 3;

function makeId(): string {
  return Math.random().toString(36).slice(2, 10);
}

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`;
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`;
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`;
}

function validateFile(file: File): string | null {
  const ext = file.name.toLowerCase().match(/\.[^.]*$/)?.[0] ?? "";
  const hasValidType =
    ACCEPTED_TYPES.includes(file.type) || ACCEPTED_EXTENSIONS.includes(ext);
  if (!hasValidType) {
    return "Unsupported file type — use JPG, PNG or WebP.";
  }
  if (file.size > MAX_BYTES) {
    return "File is over the 10MB limit.";
  }
  return null;
}

export function PhotoUploader() {
  const [items, setItems] = useState<UploadItem[]>([]);
  const [dragActive, setDragActive] = useState(false);
  const [uploading, setUploading] = useState(false);
  const inputRef = useRef<HTMLInputElement>(null);

  useEffect(() => {
    const previews = items.map((item) => item.preview);
    return () => {
      previews.forEach((preview) => URL.revokeObjectURL(preview));
    };
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, []);

  const addFiles = useCallback((incoming: FileList | File[]) => {
    const next: UploadItem[] = [];
    Array.from(incoming).forEach((file) => {
      const error = validateFile(file);
      next.push({
        id: makeId(),
        file,
        preview: URL.createObjectURL(file),
        name: file.name,
        size: file.size,
        status: error ? "error" : "pending",
        progress: 0,
        error: error ?? undefined,
      });
    });
    setItems((prev) => [...prev, ...next]);
  }, []);

  const patchItem = useCallback((id: string, patch: Partial<UploadItem>) => {
    setItems((prev) =>
      prev.map((item) => (item.id === id ? { ...item, ...patch } : item)),
    );
  }, []);

  const removeItem = useCallback((id: string) => {
    setItems((prev) => {
      const target = prev.find((item) => item.id === id);
      if (target) URL.revokeObjectURL(target.preview);
      return prev.filter((item) => item.id !== id);
    });
  }, []);

  const uploadAll = useCallback(async () => {
    const token = await getAuthToken();
    const pending = items.filter((item) => item.status === "pending");
    if (pending.length === 0) return;

    if (!token) {
      pending.forEach((item) =>
        patchItem(item.id, {
          status: "error",
          error: "You must be signed in to upload.",
        }),
      );
      return;
    }

    setUploading(true);
    let nextIndex = 0;

    const worker = async () => {
      while (nextIndex < pending.length) {
        const item = pending[nextIndex++];
        try {
          patchItem(item.id, { status: "uploading", progress: 0, error: undefined });
          const res = await uploadWardrobePhoto(item.file, token, (percent) =>
            patchItem(item.id, { progress: percent }),
          );
          const result = res.uploaded[0];
          if (result) {
            patchItem(item.id, { status: "done", progress: 100, result });
          } else {
            const message =
              res.failed[0]?.error ?? "Upload failed. Please try again.";
            patchItem(item.id, { status: "error", error: message });
          }
        } catch (err) {
          patchItem(item.id, {
            status: "error",
            error:
              err instanceof Error ? err.message : "Upload failed. Please try again.",
          });
        }
      }
    };

    const workers = Array.from(
      { length: Math.min(CONCURRENCY, pending.length) },
      () => worker(),
    );
    await Promise.all(workers);
    setUploading(false);
  }, [items, patchItem]);

  const clearFinished = useCallback(() => {
    setItems((prev) =>
      prev.filter((item) => item.status === "pending" || item.status === "uploading"),
    );
  }, []);

  const pendingCount = useMemo(
    () => items.filter((item) => item.status === "pending").length,
    [items],
  );
  const doneCount = useMemo(
    () => items.filter((item) => item.status === "done").length,
    [items],
  );

  return (
    <Card className="w-full max-w-3xl">
      <CardHeader>
        <CardTitle>Upload photos</CardTitle>
        <CardDescription>
          Add photos of garments you&apos;re considering. JPG, PNG or WebP, up to
          10MB each.
        </CardDescription>
      </CardHeader>
      <CardContent className="flex flex-col gap-4">
        <div
          role="button"
          tabIndex={0}
          onClick={() => inputRef.current?.click()}
          onKeyDown={(e) => {
            if (e.key === "Enter" || e.key === " ") {
              e.preventDefault();
              inputRef.current?.click();
            }
          }}
          onDragOver={(e) => {
            e.preventDefault();
            setDragActive(true);
          }}
          onDragLeave={() => setDragActive(false)}
          onDrop={(e) => {
            e.preventDefault();
            setDragActive(false);
            if (e.dataTransfer.files.length) {
              addFiles(e.dataTransfer.files);
            }
          }}
          className={cn(
            "flex cursor-pointer flex-col items-center justify-center gap-2 rounded-lg border-2 border-dashed p-8 text-center transition-colors",
            dragActive
              ? "border-primary bg-accent"
              : "border-border hover:border-primary/60 hover:bg-accent/50",
          )}
        >
          <input
            ref={inputRef}
            type="file"
            multiple
            accept="image/jpeg,image/png,image/webp"
            className="hidden"
            onChange={(e) => {
              if (e.target.files?.length) addFiles(e.target.files);
              e.target.value = "";
            }}
          />
          <UploadCloud className="h-8 w-8 text-muted-foreground" />
          <p className="text-sm font-medium">
            Drag &amp; drop photos here, or{" "}
            <span className="text-primary underline">browse</span>
          </p>
          <p className="text-xs text-muted-foreground">
            You can select multiple files at once.
          </p>
        </div>

        {items.length > 0 && (
          <div className="grid grid-cols-2 gap-3 sm:grid-cols-3 md:grid-cols-4">
            <AnimatePresence initial={false}>
              {items.map((item) => (
                <motion.div
                  key={item.id}
                  layout
                  initial={{ opacity: 0, scale: 0.92 }}
                  animate={{ opacity: 1, scale: 1 }}
                  exit={{ opacity: 0, scale: 0.85 }}
                  transition={{ type: "spring", stiffness: 320, damping: 24 }}
                  className="relative overflow-hidden rounded-lg border bg-card"
                >
                  <div className="relative aspect-square w-full bg-muted">
                    <img
                      src={item.preview}
                      alt={item.name}
                      className="h-full w-full object-cover"
                    />
                    <AnimatePresence>
                      {item.status === "done" && (
                        <motion.div
                          initial={{ opacity: 0, scale: 0.6 }}
                          animate={{ opacity: 1, scale: 1 }}
                          exit={{ opacity: 0 }}
                          transition={{ type: "spring", stiffness: 400, damping: 18 }}
                          className="absolute inset-0 flex items-center justify-center bg-primary/40"
                        >
                          <motion.div
                            initial={{ scale: 0 }}
                            animate={{ scale: 1 }}
                            transition={{ delay: 0.05, type: "spring", stiffness: 400, damping: 15 }}
                          >
                            <CheckCircle2 className="h-10 w-10 text-white drop-shadow" />
                          </motion.div>
                        </motion.div>
                      )}
                    </AnimatePresence>
                    {item.status === "uploading" && (
                      <div className="absolute inset-x-0 bottom-0 flex items-center gap-2 bg-black/60 px-2 py-1 text-xs text-white">
                        <Loader2 className="h-3 w-3 animate-spin" />
                        <span>{item.progress}%</span>
                      </div>
                    )}
                    <button
                      type="button"
                      onClick={() => removeItem(item.id)}
                      aria-label={`Remove ${item.name}`}
                      className="absolute right-1 top-1 rounded-full bg-black/50 p-1 text-white opacity-80 transition-opacity hover:opacity-100"
                    >
                      <X className="h-3.5 w-3.5" />
                    </button>
                  </div>
                  <div className="space-y-1 p-2">
                    <p className="truncate text-xs font-medium" title={item.name}>
                      {item.name}
                    </p>
                    <div className="flex items-center justify-between text-[11px] text-muted-foreground">
                      <span>{formatBytes(item.size)}</span>
                      {item.status === "pending" && <span>Ready</span>}
                      {item.status === "uploading" && <span>Uploading…</span>}
                      {item.status === "done" && (
                        <span className="flex items-center gap-1 text-green-600">
                          <CheckCircle2 className="h-3 w-3" /> Saved
                        </span>
                      )}
                      {item.status === "error" && (
                        <span className="flex items-center gap-1 text-red-600">
                          <AlertCircle className="h-3 w-3" /> Failed
                        </span>
                      )}
                    </div>
                    {item.status === "uploading" && (
                      <Progress value={item.progress} className="h-1.5" />
                    )}
                    {item.status === "error" && item.error && (
                      <p className="text-[11px] leading-snug text-red-600">
                        {item.error}
                      </p>
                    )}
                  </div>
                </motion.div>
              ))}
            </AnimatePresence>
          </div>
        )}

        {items.length > 0 && (
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-xs text-muted-foreground">
              {doneCount} of {items.length} uploaded
              {pendingCount > 0 && ` · ${pendingCount} waiting`}
            </p>
            <div className="flex gap-2">
              <Button variant="outline" size="sm" onClick={clearFinished}>
                Clear finished
              </Button>
              <Button size="sm" onClick={uploadAll} disabled={uploading || pendingCount === 0}>
                {uploading ? (
                  <>
                    <Loader2 className="mr-1 animate-spin" /> Uploading…
                  </>
                ) : (
                  <>
                    <FileImage className="mr-1" /> Upload {pendingCount > 0 ? `(${pendingCount})` : ""}
                  </>
                )}
              </Button>
            </div>
          </div>
        )}
      </CardContent>
    </Card>
  );
}