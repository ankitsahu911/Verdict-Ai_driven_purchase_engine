"use client";

import React from "react";
import Link from "next/link";
import { motion } from "framer-motion";
import {
  Sparkles,
  ArrowRight,
  Shirt,
  Compass,
  LayoutDashboard,
  FlaskConical,
  Scale,
  Bot,
  CheckCircle2,
  AlertTriangle,
  Zap,
  Layers,
  ShieldCheck,
  TrendingDown,
  Clock,
} from "lucide-react";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { NavigationHeader } from "@/components/NavigationHeader";

const HERO_TELEMETRY = [
  { label: "Wardrobe Constraint Graph", value: "24 Items", detail: "Locally Vectorized" },
  { label: "Evaluation Latency", value: "1.87s", detail: "End-to-End Decision" },
  { label: "Combinatorial Power", value: "2⁴ Subsets", detail: "16 Cart Combinations" },
  { label: "Cloud Lock-in", value: "0%", detail: "Local-First Resilient" },
];

const CORE_ENGINES = [
  {
    href: "/candidates",
    icon: Shirt,
    title: "Garment Intake & Try-On",
    tagline: "Vision Feature Extraction + Fit Signals",
    description:
      "Upload any online candidate garment or paste a product image. Parallel intake extracts visual attributes, searches closet redundancy, and renders virtual try-on previews.",
    badge: "Intake Flow",
  },
  {
    href: "/verdict-test",
    icon: Sparkles,
    title: "6-Axis Buy Score Radar",
    tagline: "Multivariate Purchase Decision Synthesis",
    description:
      "Holistic evaluation across 6 weighted dimensions: Redundancy, Versatility, Budget Impact, Seasonality, Style Cohesion, and Occasion Utility.",
    badge: "Decision Engine",
  },
  {
    href: "/what-if",
    icon: FlaskConical,
    title: "What-If Combinatorial Lab",
    tagline: "2^N Counterfactual Cart Optimizer",
    description:
      "Evaluates every mathematical purchasing subset ($2^N$). Identifies synergistic garment pairings, filters cannibalizing duplicates, and recommends the optimal bundle.",
    badge: "Cart Synergy",
  },
  {
    href: "/opportunity-cost",
    icon: Scale,
    title: "Opportunity Cost Trade-Off",
    tagline: "Counterfactual Resource Optimization",
    description:
      "Audits whether spending $250 on a single candidate item creates more wardrobe utility than an alternative bundle of two complementary pieces.",
    badge: "Budget Intelligence",
  },
  {
    href: "/stylist",
    icon: Bot,
    title: "Wardrobe Stylist Chat",
    tagline: "Grounded RAG Assistant (Zero Hallucination)",
    description:
      "Conversational stylist grounded exclusively in your indexed wardrobe items. Generates outfits for real occasions with zero phantom recommendations.",
    badge: "Grounded RAG",
  },
  {
    href: "/wardrobe",
    icon: Compass,
    title: "Vectorized Wardrobe Graph",
    tagline: "ChromaDB Embedding Collection",
    description:
      "Browse and manage your personal clothing constraint collection. Fully indexed with CLIP visual embeddings and structured attributes.",
    badge: "Constraint Graph",
  },
];

import { useAuth } from "@/contexts/AuthContext";
import { useRouter } from "next/navigation";
import { useEffect } from "react";

export default function Home() {
  const { user, loading } = useAuth();
  const router = useRouter();

  useEffect(() => {
    if (!loading && !user) {
      router.replace("/login");
    }
  }, [user, loading, router]);

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground">
      <NavigationHeader currentSubtitle="Decision Engine" badgeText="Enterprise Ready" />

      {/* Hero Section — Full Window Width */}
      <section className="relative w-full overflow-hidden pt-12 pb-20 border-b border-border/40">
        <div className="w-full px-4 sm:px-6 lg:px-8 xl:px-10">
          <div className="flex flex-col items-center text-center max-w-5xl mx-auto space-y-6">
            {/* Pill Badge */}
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="inline-flex items-center gap-2 px-3.5 py-1.5 rounded-full bg-secondary/80 dark:bg-[#1f172a] border border-border/80 dark:border-[#342646] shadow-sm text-xs font-medium text-foreground/90"
            >
              <span className="h-2 w-2 rounded-full brand-gradient-bg animate-pulse" />
              <span>AI Purchase Decision Engine</span>
              <span className="text-muted-foreground">•</span>
              <span className="text-primary font-semibold">Not a Wardrobe App</span>
            </motion.div>

            {/* Main Headline */}
            <motion.h1
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="font-serif text-4xl sm:text-6xl lg:text-7xl font-normal tracking-tight leading-[1.1] text-foreground"
            >
              Stop guessing. Know your{" "}
              <span className="italic font-normal">Verdict</span> before you buy.
            </motion.h1>

            {/* Subtitle */}
            <motion.p
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.2 }}
              className="text-base sm:text-xl text-muted-foreground font-normal max-w-3xl leading-relaxed"
            >
              Verdict calculates cart-level counterfactual purchase decisions against your real wardrobe graph.
              6-axis synthesis, $2^N$ combinatorial cart synergy, and deterministic Buy or Skip verdicts.
            </motion.p>

            {/* CTA Buttons */}
            <motion.div
              initial={{ opacity: 0, y: 15 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.3 }}
              className="flex flex-wrap items-center justify-center gap-4 pt-4"
            >
              <Link href="/dashboard">
                <Button
                  size="lg"
                  className="h-13 px-8 rounded-2xl bg-neutral-900 text-white font-bold text-base shadow-xl hover:bg-black transition-all flex items-center gap-2.5 cursor-pointer dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-100"
                >
                  <LayoutDashboard className="h-4.5 w-4.5" />
                  <span>Launch Decision Console</span>
                  <ArrowRight className="h-4.5 w-4.5" />
                </Button>
              </Link>
              <Link href="/what-if">
                <Button
                  variant="outline"
                  size="lg"
                  className="h-13 px-8 rounded-2xl border-2 border-neutral-300 dark:border-neutral-700 bg-white/90 dark:bg-neutral-900/90 text-foreground font-semibold text-base hover:border-neutral-900 dark:hover:border-white transition-all flex items-center gap-2.5 cursor-pointer shadow-sm"
                >
                  <FlaskConical className="h-4.5 w-4.5 text-neutral-800 dark:text-neutral-200" />
                  <span>Explore What-If Lab</span>
                </Button>
              </Link>
            </motion.div>
          </div>

          {/* Telemetry Stats Bar */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="mt-14 grid grid-cols-2 lg:grid-cols-4 gap-4 p-4 rounded-3xl glass-panel shadow-sm"
          >
            {HERO_TELEMETRY.map((stat, i) => (
              <div
                key={i}
                className="p-4 rounded-2xl bg-secondary/30 dark:bg-[#171020]/40 border border-border/40 dark:border-[#342646]/60 text-center flex flex-col justify-center"
              >
                <span className="text-2xl sm:text-3xl font-black text-foreground tracking-tight">
                  {stat.value}
                </span>
                <span className="text-xs font-semibold text-foreground/90 mt-0.5">
                  {stat.label}
                </span>
                <span className="text-[11px] text-muted-foreground font-mono mt-0.5">
                  {stat.detail}
                </span>
              </div>
            ))}
          </motion.div>
        </div>
      </section>

      {/* Decision Showcase: Hero BUY vs Hero SKIP — Spanning Desktop Width */}
      <section className="w-full py-16 border-b border-border/40 bg-secondary/15 dark:bg-[#171020]/20">
        <div className="w-full px-4 sm:px-6 lg:px-8 xl:px-10 space-y-8">
          <div className="text-center max-w-3xl mx-auto space-y-2">
            <span className="text-xs font-bold text-primary uppercase tracking-wider">
              Deterministic Decision Intelligence
            </span>
            <h2 className="text-3xl sm:text-4xl font-extrabold tracking-tight">
              One Cart. Two Distinct Verdicts.
            </h2>
            <p className="text-sm text-muted-foreground">
              Verdict doesn&apos;t just push you to buy. It prevents redundant purchases by scanning your personal closet graph.
            </p>
          </div>

          <div className="grid grid-cols-1 lg:grid-cols-2 gap-6 pt-4">
            {/* Candidate #33 (BUY) */}
            <div className="p-6 sm:p-8 rounded-3xl glass-panel border-amber-600/30 dark:border-amber-600/25 relative overflow-hidden shadow-lg">
              <div className="flex items-center justify-between gap-4 pb-4 border-b border-border/50">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-0.5 rounded-full bg-amber-600/15 text-amber-800 dark:text-amber-200 font-extrabold text-xs">
                      BUY VERDICT
                    </span>
                    <span className="text-xs text-muted-foreground font-mono">Candidate #33</span>
                  </div>
                  <h3 className="text-xl font-bold mt-1 text-foreground">
                    Minimalist Camel Trench Coat
                  </h3>
                </div>
                <div className="text-right">
                  <span className="text-3xl font-black text-amber-700 dark:text-amber-400 tracking-tight">81.2</span>
                  <span className="text-xs text-muted-foreground block font-mono">Buy Score / 100</span>
                </div>
              </div>

              <div className="mt-5 space-y-3">
                <div className="flex items-center justify-between text-xs py-2 border-b border-border/30">
                  <span className="text-muted-foreground">Wardrobe Uniqueness</span>
                  <span className="font-bold text-amber-700 dark:text-amber-400">88.0 / 100 (Only 12% Duplicate Risk)</span>
                </div>
                <div className="flex items-center justify-between text-xs py-2 border-b border-border/30">
                  <span className="text-muted-foreground">Outfit Versatility</span>
                  <span className="font-bold text-foreground">+5 Complete Outfits Unlocked</span>
                </div>
                <div className="flex items-center justify-between text-xs py-2 border-b border-border/30">
                  <span className="text-muted-foreground">Projected Cost-Per-Wear</span>
                  <span className="font-bold text-foreground">$2.80 / wear (Immediate Seasonality)</span>
                </div>
              </div>

              <p className="mt-4 text-xs text-foreground/80 leading-relaxed bg-amber-600/5 p-3.5 rounded-xl border border-amber-600/20">
                <strong>Headline Reason:</strong> Strong versatile addition with high autumn/winter utility and low duplicate risk with existing wardrobe pieces.
              </p>

              <div className="mt-5 flex justify-end">
                <Link href="/verdict-test">
                  <Button variant="ghost" size="sm" className="text-xs text-amber-700 dark:text-amber-400 hover:text-amber-600 font-semibold gap-1.5 cursor-pointer">
                    <span>Inspect 6-Axis Radar</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Button>
                </Link>
              </div>
            </div>

            {/* Candidate #32 (SKIP) */}
            <div className="p-6 sm:p-8 rounded-3xl glass-panel border-amber-500/30 dark:border-amber-500/25 relative overflow-hidden shadow-lg">
              <div className="flex items-center justify-between gap-4 pb-4 border-b border-border/50">
                <div>
                  <div className="flex items-center gap-2">
                    <span className="px-2.5 py-0.5 rounded-full bg-amber-500/10 text-amber-600 dark:text-amber-400 font-extrabold text-xs">
                      SKIP VERDICT
                    </span>
                    <span className="text-xs text-muted-foreground font-mono">Candidate #32</span>
                  </div>
                  <h3 className="text-xl font-bold mt-1 text-foreground">
                    Charcoal Wool Overshirt
                  </h3>
                </div>
                <div className="text-right">
                  <span className="text-3xl font-black text-amber-500 tracking-tight">41.0</span>
                  <span className="text-xs text-muted-foreground block font-mono">Buy Score / 100</span>
                </div>
              </div>

              <div className="mt-5 space-y-3">
                <div className="flex items-center justify-between text-xs py-2 border-b border-border/30">
                  <span className="text-muted-foreground">Wardrobe Uniqueness</span>
                  <span className="font-bold text-amber-500">4.0 / 100 (96.0% Duplicate Overlap)</span>
                </div>
                <div className="flex items-center justify-between text-xs py-2 border-b border-border/30">
                  <span className="text-muted-foreground">Closet Match Conflict</span>
                  <span className="font-bold text-foreground">Matches Item #14 (Owned 1.5 yrs)</span>
                </div>
                <div className="flex items-center justify-between text-xs py-2 border-b border-border/30">
                  <span className="text-muted-foreground">Outfit Synergy Delta</span>
                  <span className="font-bold text-muted-foreground">+0 Net New Outfits Created</span>
                </div>
              </div>

              <p className="mt-4 text-xs text-foreground/80 leading-relaxed bg-amber-500/5 p-3.5 rounded-xl border border-amber-500/20">
                <strong>Headline Reason:</strong> 96.0% similar to an item you already own — largely redundant purchase with near-zero marginal utility.
              </p>

              <div className="mt-5 flex justify-end">
                <Link href="/verdict-test">
                  <Button variant="ghost" size="sm" className="text-xs text-amber-500 hover:text-amber-400 font-semibold gap-1.5 cursor-pointer">
                    <span>Inspect 6-Axis Radar</span>
                    <ArrowRight className="h-3.5 w-3.5" />
                  </Button>
                </Link>
              </div>
            </div>
          </div>
        </div>
      </section>

      {/* Decision Engines Grid — Fluid Full Desktop Grid */}
      <section className="w-full py-16">
        <div className="w-full px-4 sm:px-6 lg:px-8 xl:px-10 space-y-10">
          <div className="flex flex-col sm:flex-row sm:items-end justify-between gap-4 pb-6 border-b border-border/40">
            <div>
              <span className="text-xs font-bold text-primary uppercase tracking-wider">
                Full-Stack Architecture
              </span>
              <h2 className="text-3xl font-extrabold tracking-tight mt-1">
                The 6 Integrated Decision Engines
              </h2>
            </div>
            <p className="text-xs sm:text-sm text-muted-foreground max-w-lg">
              Explore every layer of the Verdict intelligence pipeline directly from your personal console.
            </p>
          </div>

          <div className="grid grid-cols-1 md:grid-cols-2 xl:grid-cols-3 gap-6">
            {CORE_ENGINES.map((engine, idx) => {
              const Icon = engine.icon;
              return (
                <Link key={idx} href={engine.href} className="group block">
                  <div className="h-full p-6 sm:p-7 rounded-3xl glass-panel glass-panel-hover flex flex-col justify-between">
                    <div>
                      <div className="flex items-center justify-between gap-3 mb-4">
                        <div className="flex h-11 w-11 items-center justify-center rounded-2xl bg-secondary/80 dark:bg-[#241a30] text-primary group-hover:brand-gradient-bg group-hover:text-white transition-all shadow-sm">
                          <Icon className="h-5 w-5" />
                        </div>
                        <Badge variant="outline" className="text-[10px] font-semibold bg-secondary/50 border-border/60">
                          {engine.badge}
                        </Badge>
                      </div>

                      <h3 className="text-lg font-bold text-foreground group-hover:text-primary transition-colors">
                        {engine.title}
                      </h3>
                      <p className="text-xs font-semibold text-primary/90 mt-0.5">
                        {engine.tagline}
                      </p>
                      <p className="text-xs text-muted-foreground mt-2.5 leading-relaxed">
                        {engine.description}
                      </p>
                    </div>

                    <div className="mt-6 pt-4 border-t border-border/40 flex items-center justify-between text-xs font-semibold text-foreground/80 group-hover:text-primary transition-colors">
                      <span>Launch Engine</span>
                      <ArrowRight className="h-4 w-4 transition-transform group-hover:translate-x-1" />
                    </div>
                  </div>
                </Link>
              );
            })}
          </div>
        </div>
      </section>

      {/* Footer */}
      <footer className="w-full mt-auto py-8 border-t border-border/40 bg-secondary/10 dark:bg-[#171020]/30 text-xs text-muted-foreground">
        <div className="w-full px-4 sm:px-6 lg:px-8 xl:px-10 flex flex-col sm:flex-row items-center justify-between gap-4">
          <div className="flex items-center gap-2">
            <span className="font-extrabold text-sm text-foreground">Verdict</span>
            <span>• AI Purchase Decision Engine</span>
          </div>
          <p className="text-[11px]">
            Engineered with local-first vector search, 6-axis decision heuristics, and counterfactual What-If optimization.
          </p>
        </div>
      </footer>
    </div>
  );
}
