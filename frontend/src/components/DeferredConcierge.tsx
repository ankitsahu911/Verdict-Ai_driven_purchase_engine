"use client";

import dynamic from "next/dynamic";
import { useEffect, useState } from "react";

const VerdictConcierge = dynamic(
  () => import("@/components/VerdictConcierge").then((module) => module.VerdictConcierge),
  { ssr: false },
);

export function DeferredConcierge() {
  const [ready, setReady] = useState(false);

  useEffect(() => {
    const timer = window.setTimeout(() => setReady(true), 1200);
    return () => window.clearTimeout(timer);
  }, []);

  return ready ? <VerdictConcierge /> : null;
}
