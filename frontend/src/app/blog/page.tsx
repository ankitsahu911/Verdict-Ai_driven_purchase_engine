"use client";

import React, { useState } from "react";
import Link from "next/link";
import { NavigationHeader } from "@/components/NavigationHeader";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  BookOpen,
  Sparkles,
  ArrowRight,
  Clock,
  Shirt,
  Compass,
  Palette,
  CheckCircle2,
  Bookmark,
  Share2,
  Ruler,
  Layers,
  Coins,
  Leaf,
  ShieldCheck,
} from "lucide-react";

interface Article {
  id: string;
  category: "Styling Guides" | "Closet Economics" | "Silhouette & Fit" | "Fabric Care";
  title: string;
  excerpt: string;
  readingTime: string;
  date: string;
  author: string;
  featured?: boolean;
  content: {
    heading: string;
    body: string[];
    rules?: string[];
  }[];
}

const ARTICLES: Article[] = [
  {
    id: "silhouette-mastery",
    category: "Silhouette & Fit",
    featured: true,
    title: "The Architecture of Proportion: How to Dress for Your Natural Silhouette",
    excerpt:
      "Style is not about body size—it is about visual balance, optical line extension, and harmonic proportion. Learn the exact rule of thirds and volume balancing used by haute couture stylists.",
    readingTime: "6 min read",
    date: "October 11, 2026",
    author: "Elena Rostova, Lead Wardrobe Architect",
    content: [
      {
        heading: "1. The Rule of Thirds in Everyday Dressing",
        body: [
          "Human perception finds the 1:2 or 2:1 ratio inherently more flattering than bisecting your body 1:1 down the exact middle.",
          "When you wear an untucked shirt that cuts your body exactly in half, you visually shorten your legs. Instead, tucking your top creates a 1/3 upper body and 2/3 lower body ratio that elongates the torso and heightens your vertical line.",
        ],
        rules: [
          "High-rise trousers + tucked knitwear = Instant 1:2 vertical elongation",
          "Cropped jackets draw the eye upward and accentuate the natural waistline",
          "Long duster coats should fall either mid-calf or ankle—avoid cutting off precisely at the knee",
        ],
      },
      {
        heading: "2. The Counterweight Principle: Volume Contrasts",
        body: [
          "The most common styling mistake is wearing oversized pieces top and bottom simultaneously without structure, or conversely, wearing skin-tight pieces everywhere.",
          "High-end sartorial balance relies on the counterweight rule: pair relaxed, voluminous wide-leg trousers with a structured, tailored, or form-fitting top. Conversely, when wearing relaxed oversized knitwear, ground it with clean, slim-tapered trousers or sleek boots.",
        ],
      },
      {
        heading: "3. Shoulder Seams: The Keystone of Tailoring",
        body: [
          "Unless a garment is deliberately cut with a drop-shoulder or raglan sleeve, the shoulder seam must terminate exactly where your acromion bone ends. Even a 1-centimeter overhang creates a sloppy, borrowed silhouette.",
        ],
      },
    ],
  },
  {
    id: "closet-economics",
    category: "Closet Economics",
    title: "Cost-Per-Wear Amortization: The True Financial Equation of Luxury",
    excerpt:
      "A $350 cashmere overcoat worn 120 times costs $2.91 per wear. A $40 synthetic impulse purchase worn twice costs $20.00 per wear. How to mathematically evaluate your wardrobe return on capital.",
    readingTime: "5 min read",
    date: "October 10, 2026",
    author: "Marcus Chen, Closet Quant Strategist",
    content: [
      {
        heading: "The 30-Wear Threshold",
        body: [
          "Before authorizing any checkout, ask: will this garment realistically achieve at least 30 wears across the next 24 months?",
          "If the answer is no, the cost-per-wear penalty is astronomical. Special occasion garments should be rented or borrowed unless they possess multi-occasion versatility.",
        ],
        rules: [
          "Never calculate value by the purchase sticker price alone",
          "Versatile core neutrals yield 4x more outfits than bright novelty prints",
          "Low cost-per-wear justifies investing in exceptional natural fibers",
        ],
      },
    ],
  },
  {
    id: "color-theory",
    category: "Styling Guides",
    title: "Color Harmony & Optical Cohesion: Building a 3-Tone Capsule",
    excerpt:
      "Mastering the 60-30-10 color rule. How anchoring outfits around two complementary neutrals and one controlled accent creates timeless, quiet luxury aesthetics.",
    readingTime: "4 min read",
    date: "October 9, 2026",
    author: "Elena Rostova",
    content: [
      {
        heading: "The 60-30-10 Sartorial Distribution",
        body: [
          "60% Dominant Base: Your trousers or outerwear (e.g., Midnight Charcoal or Deep Cocoa).",
          "30% Secondary Neutral: Your knitwear or shirt (e.g., Ivory Cream or Warm Oatmeal).",
          "10% Accent Accentuation: Leather belt, watch leather, scarf, or footwear (e.g., Cognac Camel or Antique Gold).",
        ],
        rules: [
          "Never introduce more than 3 distinct hues into a single daytime ensemble",
          "Warm skin undertones radiate in cognac, camel, and warm cream",
          "Cool skin undertones achieve crisp contrast in charcoal, espresso, and pure white",
        ],
      },
    ],
  },
  {
    id: "fabric-care",
    category: "Fabric Care",
    title: "Fiber Longevity & Material Science: How to Preserve Natural Textiles",
    excerpt:
      "Why dry cleaning destroys wool fibers, the correct way to de-pill Mongolian cashmere, and why cedar wood repels moths without harsh chemicals.",
    readingTime: "4 min read",
    date: "October 8, 2026",
    author: "Dr. Aris Thorne, Textile Conservator",
    content: [
      {
        heading: "Natural Fibers vs. Microplastic Blends",
        body: [
          "Cashmere and merino possess natural lanolin coatings that resist bacterial growth and odor without frequent chemical dry-cleaning.",
          "Air out wool garments between wears on cedar hangers rather than washing after every use.",
        ],
        rules: [
          "Rest wool garments 24 hours between wears to allow natural crimp elasticity to rebound",
          "Steam rather than press iron delicate silks to preserve natural sheen",
          "Store knitwear folded flat—never on wire or thin hangers",
        ],
      },
    ],
  },
];

export default function BlogPage() {
  const [selectedCategory, setSelectedCategory] = useState<string>("All");
  const [expandedArticleId, setExpandedArticleId] = useState<string | null>("silhouette-mastery");

  const categories = ["All", "Silhouette & Fit", "Closet Economics", "Styling Guides", "Fabric Care"];

  const filtered = selectedCategory === "All"
    ? ARTICLES
    : ARTICLES.filter((a) => a.category === selectedCategory);

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground transition-colors duration-200">
      <NavigationHeader currentSubtitle="Editorial Style Guide" badgeText="Curated Advice" />

      {/* EXPANSIVE WIDESCREEN CONTAINER — NO SIDE WASTED SPACE, PURE BROWN & WHITE LUXURY PALETTE */}
      <main className="w-full flex-1 py-8 px-4 sm:px-6 lg:px-10 xl:px-14 max-w-[1780px] 2xl:max-w-[1920px] mx-auto space-y-8">
        {/* Header Hero Banner in Warm Cognac Brown & White Palette */}
        <div className="relative overflow-hidden rounded-3xl border border-amber-600/30 bg-gradient-to-r from-amber-600/10 via-card to-amber-600/5 p-6 sm:p-10 backdrop-blur-md shadow-sm">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-3 max-w-4xl">
              <div className="flex flex-wrap items-center gap-2.5">
                <Badge className="bg-amber-600/15 text-amber-800 dark:text-amber-200 border-amber-600/30 text-xs font-bold px-3 py-1">
                  <BookOpen className="h-3.5 w-3.5 mr-1 text-amber-600" />
                  Verdict Editorial & Styling Architecture
                </Badge>
                <Badge variant="outline" className="border-border text-muted-foreground text-xs font-semibold">
                  Sartorial Science
                </Badge>
              </div>
              <h1 className="text-3xl sm:text-5xl font-serif font-black tracking-tight text-foreground leading-tight">
                The Art & Mathematics of Personal Style
              </h1>
              <p className="text-sm sm:text-base text-muted-foreground leading-relaxed">
                Essential guidelines on proportion, optical line extension, color harmony, and cost-per-wear economics. Grounded in timeless sartorial principles to make dressing intentional, effortless, and elegant.
              </p>
            </div>

            <div className="flex items-center gap-3 shrink-0">
              <Link href="/fitting-room">
                <Button
                  size="lg"
                  className="h-12 px-6 rounded-2xl font-bold text-xs sm:text-sm bg-neutral-900 text-white hover:bg-black dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-100 shadow-md gap-2.5 cursor-pointer transition-transform hover:scale-[1.02]"
                >
                  <Ruler className="h-4 w-4 text-amber-600 dark:text-amber-400" />
                  <span>Configure Fit Profile</span>
                  <ArrowRight className="h-4 w-4" />
                </Button>
              </Link>
            </div>
          </div>

          {/* Category Filter Pills in Warm Brown & White Style */}
          <div className="flex flex-wrap items-center gap-2.5 pt-6 border-t border-border/60 mt-6">
            {categories.map((cat) => {
              const isActive = selectedCategory === cat;
              return (
                <button
                  key={cat}
                  onClick={() => setSelectedCategory(cat)}
                  className={`px-4 py-2 rounded-2xl text-xs sm:text-sm font-bold transition-all cursor-pointer ${
                    isActive
                      ? "bg-amber-600 text-white shadow-sm"
                      : "bg-card border border-border/80 text-muted-foreground hover:text-foreground hover:bg-muted/40"
                  }`}
                >
                  {cat}
                </button>
              );
            })}
          </div>
        </div>

        {/* 2-COLUMN WIDESCREEN EDITORIAL MAGAZINE LAYOUT */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
          {/* LEFT COLUMN: SARTORIAL PILLARS SIDEBAR (4 cols) — WARM BROWN & WHITE */}
          <div className="lg:col-span-4 space-y-6">
            {/* Color Theory & Harmonic Palette Card */}
            <Card className="border border-border/80 bg-card rounded-3xl p-6 shadow-sm space-y-4 hover:border-amber-600/30 transition-colors">
              <div className="flex items-center justify-between border-b border-border/60 pb-3">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-xl bg-amber-600/10 text-amber-700 dark:text-amber-300">
                    <Palette className="h-4 w-4" />
                  </div>
                  <span className="font-serif font-bold text-base text-foreground">Color Theory Anchors</span>
                </div>
                <Badge className="bg-amber-600/15 text-amber-800 dark:text-amber-200 border-amber-600/30 text-[10px]">
                  60-30-10 Rule
                </Badge>
              </div>

              <div className="space-y-3">
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Quiet luxury relies on low-saturation anchors with deliberate warm accent points:
                </p>

                <div className="space-y-2">
                  {[
                    { label: "60% Base Anchor", hex: "#1F1D1A", text: "Charcoal Obsidian — Trousers & Overcoats" },
                    { label: "30% Neutral Bridge", hex: "#FAF7F2", text: "Ivory Cream — Shirts & Fine Knitwear" },
                    { label: "10% High Focal Accent", hex: "#AD7E4A", text: "Cognac Camel — Footwear & Leather Goods" },
                    { label: "Warm Bronze Accent", hex: "#C29B38", text: "Antique Gold — Jewelry & Hardware" },
                  ].map((c, i) => (
                    <div key={i} className="flex items-center gap-3 p-2.5 rounded-2xl border bg-muted/20">
                      <div className="h-7 w-7 rounded-xl border shadow-xs shrink-0" style={{ backgroundColor: c.hex }} />
                      <div className="min-w-0 flex-1">
                        <span className="text-xs font-bold text-foreground block">{c.label}</span>
                        <p className="text-[10px] text-muted-foreground truncate">{c.text}</p>
                      </div>
                    </div>
                  ))}
                </div>
              </div>
            </Card>

            {/* Rule of Thirds Proportion Card */}
            <Card className="border border-border/80 bg-card rounded-3xl p-6 shadow-sm space-y-4 hover:border-amber-600/30 transition-colors">
              <div className="flex items-center justify-between border-b border-border/60 pb-3">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-xl bg-amber-600/10 text-amber-700 dark:text-amber-300">
                    <Ruler className="h-4 w-4" />
                  </div>
                  <span className="font-serif font-bold text-base text-foreground">Rule of Thirds (1:2)</span>
                </div>
                <Badge className="bg-amber-600/15 text-amber-800 dark:text-amber-200 border-amber-600/30 text-[10px]">
                  Golden Ratio
                </Badge>
              </div>

              <div className="space-y-3">
                <p className="text-xs text-muted-foreground leading-relaxed">
                  Never bisect your silhouette 50/50 down the middle. Tuck knitwear into high-rise trousers to divide the body into 1/3 torso and 2/3 legs:
                </p>

                {/* Visual Proportion Bar Diagram in Brown & White */}
                <div className="p-3.5 rounded-2xl border bg-muted/20 space-y-2">
                  <div className="flex items-center justify-between text-[11px] font-bold">
                    <span className="text-amber-800 dark:text-amber-300">1/3 Torso & Top</span>
                    <span className="text-foreground">2/3 Legs & Trousers</span>
                  </div>
                  <div className="flex h-3 rounded-full overflow-hidden border border-border">
                    <div className="w-1/3 bg-amber-600" />
                    <div className="w-2/3 bg-neutral-800 dark:bg-neutral-200" />
                  </div>
                  <p className="text-[10px] text-muted-foreground text-center">
                    Creates instant optical vertical elongation and balanced stature.
                  </p>
                </div>
              </div>
            </Card>

            {/* Fiber Quality Hierarchy Card */}
            <Card className="border border-border/80 bg-card rounded-3xl p-6 shadow-sm space-y-4 hover:border-amber-600/30 transition-colors">
              <div className="flex items-center justify-between border-b border-border/60 pb-3">
                <div className="flex items-center gap-2">
                  <div className="p-1.5 rounded-xl bg-amber-600/10 text-amber-700 dark:text-amber-300">
                    <Leaf className="h-4 w-4" />
                  </div>
                  <span className="font-serif font-bold text-base text-foreground">Fiber Longevity Hierarchy</span>
                </div>
                <Badge className="bg-amber-600/15 text-amber-800 dark:text-amber-200 border-amber-600/30 text-[10px]">
                  Tier 1 Fibers
                </Badge>
              </div>

              <div className="space-y-2.5 text-xs">
                {[
                  { fiber: "2-Ply Grade A Cashmere", wear: "150+ Wears", note: "Natural crimp; rebounds with rest" },
                  { fiber: "240gsm Combed Cotton", wear: "100+ Wears", note: "Resists collar warping & wash shrinkage" },
                  { fiber: "Mulberry Silk (19mm+)", wear: "80+ Wears", note: "Hypoallergenic fluid bias drape" },
                  { fiber: "Synthetic Blends", wear: "< 15 Wears", note: "Rapid surface pilling & microplastic loss" },
                ].map((item, idx) => (
                  <div key={idx} className="flex items-center justify-between p-2 rounded-xl border bg-card/60">
                    <div>
                      <p className="font-bold text-foreground text-[11px]">{item.fiber}</p>
                      <p className="text-[10px] text-muted-foreground">{item.note}</p>
                    </div>
                    <Badge variant="outline" className="text-[10px] font-mono shrink-0 ml-2">
                      {item.wear}
                    </Badge>
                  </div>
                ))}
              </div>
            </Card>
          </div>

          {/* RIGHT COLUMN: MAIN ARTICLE MAGAZINE FEED (8 cols) */}
          <div className="lg:col-span-8 space-y-8">
            {filtered.map((article) => {
              const isExpanded = expandedArticleId === article.id;
              return (
                <Card
                  key={article.id}
                  className={`border border-border/80 bg-card rounded-3xl overflow-hidden shadow-sm transition-all hover:shadow-md ${
                    article.featured ? "border-amber-600/40" : ""
                  }`}
                >
                  <CardHeader className="p-6 sm:p-8 border-b border-border/60 bg-muted/10 space-y-3">
                    <div className="flex flex-wrap items-center justify-between gap-3">
                      <div className="flex items-center gap-2">
                        <Badge
                          variant="outline"
                          className="bg-amber-600/15 text-amber-800 dark:text-amber-200 border-amber-600/30 font-bold text-xs px-2.5 py-0.5"
                        >
                          {article.category}
                        </Badge>
                        {article.featured && (
                          <Badge className="bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 text-xs font-bold px-2.5 py-0.5">
                            ★ Editor&apos;s Pick
                          </Badge>
                        )}
                      </div>
                      <div className="flex items-center gap-4 text-xs text-muted-foreground font-medium">
                        <span className="flex items-center gap-1.5">
                          <Clock className="h-3.5 w-3.5 text-amber-600" />
                          {article.readingTime}
                        </span>
                        <span>{article.date}</span>
                      </div>
                    </div>

                    <CardTitle className="text-2xl sm:text-3xl font-serif font-black tracking-tight text-foreground leading-snug">
                      {article.title}
                    </CardTitle>
                    <p className="text-xs sm:text-sm text-muted-foreground font-normal leading-relaxed">
                      {article.excerpt}
                    </p>
                    <div className="text-xs font-semibold text-foreground/80 pt-1 flex items-center gap-2">
                      <span className="h-2 w-2 rounded-full bg-amber-600" />
                      <span>By {article.author}</span>
                    </div>
                  </CardHeader>

                  <CardContent className="p-6 sm:p-8 space-y-6">
                    {/* Always visible intro */}
                    {article.content.slice(0, isExpanded ? article.content.length : 1).map((sec, i) => (
                      <div key={i} className="space-y-3">
                        <h3 className="text-lg font-serif font-bold text-foreground">
                          {sec.heading}
                        </h3>
                        {sec.body.map((p, pIdx) => (
                          <p key={pIdx} className="text-sm text-foreground/85 leading-relaxed font-normal">
                            {p}
                          </p>
                        ))}
                        {sec.rules && (
                          <div className="mt-4 p-5 rounded-2xl border border-amber-600/30 bg-amber-600/5 space-y-2.5">
                            <span className="text-xs font-bold uppercase tracking-wider text-amber-800 dark:text-amber-300 flex items-center gap-1.5">
                              <Sparkles className="h-3.5 w-3.5 text-amber-600" />
                              Essential Rules to Remember:
                            </span>
                            <ul className="space-y-2 text-xs sm:text-sm text-foreground">
                              {sec.rules.map((rule, rIdx) => (
                                <li key={rIdx} className="flex items-start gap-2">
                                  <CheckCircle2 className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0 mt-0.5" />
                                  <span>{rule}</span>
                                </li>
                              ))}
                            </ul>
                          </div>
                        )}
                      </div>
                    ))}

                    <div className="flex flex-wrap items-center justify-between gap-4 pt-4 border-t border-border/60">
                      <Button
                        variant="outline"
                        size="sm"
                        onClick={() => setExpandedArticleId(isExpanded ? null : article.id)}
                        className="text-xs sm:text-sm font-semibold h-10 px-5 rounded-xl border-border bg-card hover:bg-muted cursor-pointer"
                      >
                        {isExpanded ? "Collapse Guide" : "Read Full Guide"}
                      </Button>

                      <div className="flex items-center gap-2">
                        <Link href="/fitting-room">
                          <Button
                            size="sm"
                            className="text-xs sm:text-sm font-bold h-10 px-5 rounded-xl bg-neutral-900 text-white hover:bg-black dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-100 gap-2 cursor-pointer shadow-sm"
                          >
                            <span>Test on Your Proportions</span>
                            <ArrowRight className="h-4 w-4" />
                          </Button>
                        </Link>
                      </div>
                    </div>
                  </CardContent>
                </Card>
              );
            })}
          </div>
        </div>
      </main>
    </div>
  );
}
