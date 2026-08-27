"use client";

import React from "react";
import { AlertCircle, CheckCircle2, Sparkles } from "lucide-react";
import { Card, CardContent } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import type { NearDuplicateMatch } from "@/lib/api";

export interface NearDuplicateCardProps {
  match: NearDuplicateMatch | null;
  hasDuplicate: boolean;
  loading?: boolean;
  className?: string;
}

export function NearDuplicateCard({
  match,
  hasDuplicate,
  loading = false,
  className = "",
}: NearDuplicateCardProps) {
  if (loading) {
    return (
      <Card className={`overflow-hidden border-dashed ${className}`}>
        <CardContent className="flex items-center gap-4 p-4">
          <div className="h-14 w-14 animate-pulse rounded-md bg-muted" />
          <div className="flex-1 space-y-2">
            <div className="h-4 w-32 animate-pulse rounded bg-muted" />
            <div className="h-3 w-48 animate-pulse rounded bg-muted" />
          </div>
        </CardContent>
      </Card>
    );
  }

  if (!hasDuplicate || !match) {
    return (
      <Card className={`border-emerald-500/30 bg-emerald-500/5 ${className}`}>
        <CardContent className="flex items-center gap-3 p-4">
          <CheckCircle2 className="h-5 w-5 text-emerald-500 shrink-0" />
          <div className="flex-1">
            <div className="flex items-center gap-2">
              <span className="text-sm font-semibold text-emerald-600 dark:text-emerald-400">
                Unique Addition
              </span>
              <Badge variant="outline" className="border-emerald-500/40 text-emerald-600 dark:text-emerald-400 text-[10px]">
                No Duplicates
              </Badge>
            </div>
            <p className="text-xs text-muted-foreground mt-0.5">
              No visually similar items found in your wardrobe.
            </p>
          </div>
        </CardContent>
      </Card>
    );
  }

  const categoryName = match.category || "item";
  const pct = match.similarity_percentage;

  return (
    <Card className={`overflow-hidden border-amber-500/40 bg-amber-500/5 shadow-sm transition-all ${className}`}>
      <CardContent className="p-4">
        <div className="flex items-start justify-between gap-2 mb-3">
          <div className="flex items-center gap-1.5 text-amber-600 dark:text-amber-400">
            <AlertCircle className="h-4 w-4 shrink-0" />
            <span className="text-xs font-semibold uppercase tracking-wider">
              Near-Duplicate Detected
            </span>
          </div>
          <Badge className="bg-amber-500 text-amber-950 font-bold hover:bg-amber-500/90 text-xs px-2 py-0.5">
            <Sparkles className="mr-1 h-3 w-3 inline" />
            {pct}% Similar
          </Badge>
        </div>

        <div className="flex items-center gap-3.5">
          {match.cloudinary_url ? (
            <div className="relative aspect-square h-16 w-16 shrink-0 overflow-hidden rounded-md border border-amber-500/30 bg-muted">
              <img
                src={match.cloudinary_url}
                alt={categoryName}
                className="h-full w-full object-cover"
              />
            </div>
          ) : (
            <div className="flex h-16 w-16 shrink-0 items-center justify-center rounded-md border border-amber-500/30 bg-muted text-xs font-medium text-muted-foreground">
              No Image
            </div>
          )}

          <div className="flex-1 min-w-0">
            <p className="text-sm font-medium text-foreground leading-snug">
              {pct}% similar to a <span className="font-semibold text-amber-600 dark:text-amber-400 capitalize">{categoryName}</span> you already own.
            </p>
            <p className="text-xs text-muted-foreground mt-1">
              Existing Item ID: <code className="rounded bg-muted px-1.5 py-0.5 text-[11px] font-mono">#{match.wardrobe_item_id}</code>
            </p>
          </div>
        </div>
      </CardContent>
    </Card>
  );
}
