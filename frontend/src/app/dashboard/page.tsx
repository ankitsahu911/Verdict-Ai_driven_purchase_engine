"use client";

import { useEffect, useState } from "react";
import Link from "next/link";
import { signOut } from "firebase/auth";
import { useRouter } from "next/navigation";
import { motion } from "framer-motion";
import {
  LayoutDashboard,
  LogOut,
  Shirt,
  Compass,
  Sparkles,
  FlaskConical,
  Scale,
  Bot,
  UserCheck,
  UploadCloud,
  CheckCircle2,
} from "lucide-react";
import { auth } from "@/lib/firebase";
import { apiFetch, type DecisionSummaryMetricsData } from "@/lib/api";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { PhotoUploader } from "@/components/PhotoUploader";
import { NavigationHeader } from "@/components/NavigationHeader";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { DecisionSummaryPanel } from "@/components/DecisionSummaryPanel";
import {
  fadeUpVariants,
  staggerContainerVariants,
  staggerItemVariants,
  cardHoverMotion,
} from "@/lib/animations";

interface MeResponse {
  uid: string;
  email: string;
}

const DEMO_DASHBOARD_METRICS: DecisionSummaryMetricsData = {
  versatility: 82.5,
  versatility_outfits_count: 5,
  duplicate_risk: 12.0,
  duplicate_risk_label: "12.0% similarity to wardrobe (Low duplicate risk)",
  seasonality: 92.0,
  seasonality_label: "In-Season (Immediate autumn/winter utility)",
  cost_per_wear: 2.8,
  cost_per_wear_formatted: "$2.80 / wear",
  sustainability_tier: "Lower impact",
  sustainability_reason: "Rough estimate based on natural fibers. Not a certified rating.",
  is_estimate: true,
};

const ENGINE_SHORTCUTS = [
  {
    href: "/candidates",
    title: "Evaluate Garment",
    description: "Multi-agent intake with virtual try-on and instant buy verdict.",
    icon: Shirt,
    badge: "Intake Flow",
  },
  {
    href: "/verdict-test",
    title: "Verdict Visualizer",
    description: "6-axis radar visualizer explaining the purchase decision.",
    icon: Sparkles,
    badge: "M24 Radar",
  },
  {
    href: "/what-if",
    title: "What-If Lab",
    description: "Combinatorial cart optimizer ranking all 2^N purchasing subsets.",
    icon: FlaskConical,
    badge: "Cart Synergy",
  },
  {
    href: "/opportunity-cost",
    title: "Opportunity Cost",
    description: "Compare one expensive piece against a 2-item alternative bundle.",
    icon: Scale,
    badge: "M28 Compare",
  },
  {
    href: "/stylist",
    title: "Stylist Chat",
    description: "Wardrobe-grounded conversational styling with zero hallucination.",
    icon: Bot,
    badge: "Grounded RAG",
  },
  {
    href: "/wardrobe",
    title: "Wardrobe Grid",
    description: "Explore your vectorized clothing collection and edit attributes.",
    icon: Compass,
    badge: "ChromaDB",
  },
];

export default function DashboardPage() {
  return (
    <ProtectedRoute>
      <DashboardContent />
    </ProtectedRoute>
  );
}

function DashboardContent() {
  const [me, setMe] = useState<MeResponse | null>(null);
  const [error, setError] = useState("");
  const router = useRouter();

  useEffect(() => {
    apiFetch("/api/me")
      .then((data) => setMe(data as MeResponse))
      .catch((err) => setError(err.message));
  }, []);

  async function handleLogout() {
    if (auth) await signOut(auth);
    router.push("/login");
  }

  return (
    <main className="min-h-screen bg-gradient-to-b from-background via-background to-muted/20 pb-16">
      <NavigationHeader currentSubtitle="Purchase Dashboard" badgeText="User Console" />

      <div className="mx-auto max-w-7xl px-4 sm:px-6 lg:px-8 py-8 sm:py-10 space-y-8">
        {/* User Hero Banner */}
        <motion.div
          initial="hidden"
          animate="visible"
          variants={fadeUpVariants}
          className="flex flex-col sm:flex-row sm:items-center justify-between gap-4 pb-6 border-b"
        >
          <div>
            <div className="flex items-center gap-2 text-primary font-bold text-xs uppercase tracking-wider mb-1">
              <LayoutDashboard className="h-4 w-4" />
              <span>Personal Console</span>
            </div>
            <h1 className="text-3xl sm:text-4xl font-black tracking-tight text-foreground">
              Decision Dashboard
            </h1>
            <p className="text-xs sm:text-sm text-muted-foreground mt-1">
              Manage your wardrobe inputs, explore purchase engines, and audit decision metrics.
            </p>
          </div>

          <div className="flex items-center gap-3">
            {me && (
              <div className="hidden sm:flex flex-col items-end text-xs">
                <span className="font-bold text-foreground truncate max-w-[200px]">{me.email}</span>
                <span className="font-mono text-[10px] text-muted-foreground truncate max-w-[160px]">
                  UID: {me.uid.slice(0, 10)}…
                </span>
              </div>
            )}
            <Button
              variant="outline"
              size="sm"
              onClick={handleLogout}
              className="gap-1.5 text-xs font-semibold rounded-xl border-border"
            >
              <LogOut className="h-3.5 w-3.5" />
              Log Out
            </Button>
          </div>
        </motion.div>

        {error && (
          <div className="rounded-2xl bg-destructive/10 p-4 text-sm text-destructive border border-destructive/20 font-medium">
            Error loading session: {error}
          </div>
        )}

        {/* Milestone 31: Purchase Dashboard Panel Showcase */}
        <motion.div
          initial="hidden"
          animate="visible"
          variants={fadeUpVariants}
        >
          <Card className="rounded-2xl border shadow-sm bg-card overflow-hidden">
            <CardHeader className="pb-3 border-b bg-muted/10">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <div>
                  <CardTitle className="text-base font-bold flex items-center gap-2">
                    <CheckCircle2 className="h-5 w-5 text-emerald-600" />
                    Purchase Dashboard Metrics (M31)
                  </CardTitle>
                  <CardDescription className="text-xs text-muted-foreground">
                    Comprehensive multi-dimensional decision telemetry applied across cart and wardrobe items.
                  </CardDescription>
                </div>
                <Badge variant="buy" className="text-xs font-bold w-fit">
                  Standardized Panel
                </Badge>
              </div>
            </CardHeader>
            <CardContent className="p-6">
              <DecisionSummaryPanel metrics={DEMO_DASHBOARD_METRICS} />
            </CardContent>
          </Card>
        </motion.div>

        {/* Engine Navigation Shortcuts Grid */}
        <div className="space-y-4">
          <div className="flex items-center justify-between pb-1 border-b">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Core Decision Engines
            </span>
            <span className="text-xs text-muted-foreground font-medium">6 Specialized Flows</span>
          </div>

          <motion.div
            initial="hidden"
            animate="visible"
            variants={staggerContainerVariants}
            className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-3 gap-4"
          >
            {ENGINE_SHORTCUTS.map((engine) => {
              const Icon = engine.icon;
              return (
                <motion.div
                  key={engine.href}
                  variants={staggerItemVariants}
                  {...cardHoverMotion}
                >
                  <Link href={engine.href} className="block h-full">
                    <Card className="h-full rounded-2xl border shadow-xs transition-all hover:shadow-md hover:border-primary/40 bg-card p-5 flex flex-col justify-between space-y-4">
                      <div className="flex items-start justify-between gap-3">
                        <div className="flex h-10 w-10 items-center justify-center rounded-xl bg-primary/10 text-primary">
                          <Icon className="h-5 w-5" />
                        </div>
                        <Badge variant="outline" className="text-[10px] font-bold border-muted-foreground/30">
                          {engine.badge}
                        </Badge>
                      </div>

                      <div>
                        <h3 className="font-black text-sm text-foreground">{engine.title}</h3>
                        <p className="text-xs text-muted-foreground mt-1 leading-relaxed">
                          {engine.description}
                        </p>
                      </div>
                    </Card>
                  </Link>
                </motion.div>
              );
            })}
          </motion.div>
        </div>

        {/* Wardrobe Photo Uploader Section */}
        <motion.div
          initial="hidden"
          animate="visible"
          variants={fadeUpVariants}
          className="space-y-3"
        >
          <div className="flex items-center justify-between pb-1 border-b">
            <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground">
              Wardrobe Photo Upload
            </span>
            <Badge variant="outline" className="text-[10px] font-semibold">
              ChromaDB Auto-Ingest
            </Badge>
          </div>

          <Card className="rounded-2xl border shadow-sm bg-card overflow-hidden">
            <CardContent className="p-6">
              <PhotoUploader />
            </CardContent>
          </Card>
        </motion.div>
      </div>
    </main>
  );
}
