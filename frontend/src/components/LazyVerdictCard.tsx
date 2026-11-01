"use client";

import dynamic from "next/dynamic";
import type { ComponentProps } from "react";
import type { VerdictCard } from "@/components/VerdictCard";

const DeferredVerdictCard = dynamic(
  () => import("@/components/VerdictCard").then((module) => module.VerdictCard),
  {
    ssr: false,
    loading: () => (
      <div className="min-h-56 animate-pulse rounded-2xl border border-border bg-card" />
    ),
  },
);

export function LazyVerdictCard(props: ComponentProps<typeof VerdictCard>) {
  return <DeferredVerdictCard {...props} />;
}
