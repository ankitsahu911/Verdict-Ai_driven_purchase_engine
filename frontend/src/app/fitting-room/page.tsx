"use client";

import React, { useState, useMemo } from "react";
import { NavigationHeader } from "@/components/NavigationHeader";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import {
  Ruler,
  CheckCircle2,
  Sparkles,
  Info,
  Sliders,
  Download,
  RotateCcw,
  Scissors,
  Check,
  HelpCircle,
  Shirt,
  Layers,
  ArrowRight,
  Palette,
  Compass,
} from "lucide-react";

export interface UserBodyMeasurements {
  // Stature
  height: number; // cm
  torsoLength: number; // cm
  inseam: number; // cm
  // Upper body
  chest: number; // cm
  underbust: number; // cm
  shoulders: number; // cm
  neck: number; // cm
  armLength: number; // cm
  // Core & Lower body
  waist: number; // cm
  highHip: number; // cm
  hips: number; // cm
  thigh: number; // cm
  // Footwear & Fit
  shoeSizeEU: number;
  fitPreference: "slim" | "tailored" | "relaxed" | "oversized";
}

const DEFAULT_MEASUREMENTS: UserBodyMeasurements = {
  height: 175,
  torsoLength: 46,
  inseam: 79,
  chest: 96,
  underbust: 80,
  shoulders: 44,
  neck: 38,
  armLength: 62,
  waist: 78,
  highHip: 88,
  hips: 98,
  thigh: 56,
  shoeSizeEU: 41,
  fitPreference: "tailored",
};

// Preset Archetypes in Cohesive Luxury Brown & White / Charcoal
const ARCHETYPE_PRESETS = [
  {
    name: "hourglass",
    label: "Harmonic Hourglass",
    desc: "Balanced bust and hips with a clearly defined waist indentation.",
    tag: "Balanced Curve",
    values: {
      chest: 96,
      underbust: 78,
      waist: 72,
      hips: 98,
      shoulders: 41,
      height: 168,
      inseam: 76,
    },
  },
  {
    name: "athletic",
    label: "Athletic V-Taper",
    desc: "Broad sculpted shoulders and chest tapering to a trim waist and hips.",
    tag: "Athletic Breadth",
    values: {
      chest: 104,
      underbust: 86,
      waist: 80,
      hips: 94,
      shoulders: 47,
      height: 180,
      inseam: 82,
    },
  },
  {
    name: "rectangular",
    label: "Balanced Rectangular",
    desc: "Even athletic alignment across shoulders, chest, waist, and hips.",
    tag: "Linear Balance",
    values: {
      chest: 92,
      underbust: 80,
      waist: 78,
      hips: 92,
      shoulders: 43,
      height: 174,
      inseam: 80,
    },
  },
  {
    name: "pear",
    label: "Graceful Pear / Triangle",
    desc: "Gentle shoulders and bust gracefully transitioning into fuller hips.",
    tag: "Lower Volume",
    values: {
      chest: 88,
      underbust: 76,
      waist: 74,
      hips: 102,
      shoulders: 39,
      height: 165,
      inseam: 74,
    },
  },
];

export default function SizeAndFitProfilePage() {
  const [measurements, setMeasurements] = useState<UserBodyMeasurements>(() => {
    if (typeof window !== "undefined") {
      try {
        const saved = localStorage.getItem("verdict_user_measurements");
        if (saved) {
          const parsed = JSON.parse(saved);
          return { ...DEFAULT_MEASUREMENTS, ...parsed };
        }
      } catch {
        // fallback
      }
    }
    return DEFAULT_MEASUREMENTS;
  });

  const [unit, setUnit] = useState<"cm" | "in">("cm");
  const [activeTab, setActiveTab] = useState<"profile" | "sizematrix" | "guidelines">("profile");
  const [saveSuccess, setSaveSuccess] = useState<boolean>(false);
  const [exportSuccess, setExportSuccess] = useState<boolean>(false);

  // Conversion Helpers
  const toDisplay = (valCm: number) => {
    if (unit === "cm") return `${Math.round(valCm)} cm`;
    const inches = valCm / 2.54;
    return `${inches.toFixed(1)} in`;
  };

  // Body Proportion Silhouette Analysis
  const bodyShapeAnalysis = useMemo(() => {
    const { chest, waist, hips, shoulders } = measurements;
    const chestWaistDrop = chest - waist;
    const waistHipRatio = waist / (hips || 1);
    const shoulderWaistRatio = shoulders / (waist / 2 || 1);

    let archetype = "Proportional Tailored Frame";
    let summary = "Balanced proportions suitable for versatile classic tailoring.";
    let stylingAdvice = "Clean vertical lines, natural shoulder drops, and classic tailored waist suppression harmonize with your proportions.";
    let colorPalette = [
      { name: "Cognac Camel", hex: "#AD7E4A", text: "Warm Midtones" },
      { name: "Ivory Cream", hex: "#FAF7F2", text: "Classic Anchors" },
      { name: "Charcoal Slate", hex: "#334155", text: "Tailored Base" },
      { name: "Rich Umber", hex: "#4A3B32", text: "Deep Accent" },
    ];

    if (chestWaistDrop > 18 && hips - waist < 14) {
      archetype = "Athletic V-Taper";
      summary = "Sculpted shoulder and chest breadth with athletic waist drop.";
      stylingAdvice = "Look for unstructured soft shoulders, unlined blazers, and slim-tapered trousers that don't pull across the chest.";
      colorPalette = [
        { name: "Warm Camel", hex: "#AD7E4A", text: "Broadening Anchor" },
        { name: "Pure Ivory", hex: "#FAF7F2", text: "Clean Crisp" },
        { name: "Espresso Brown", hex: "#3E2723", text: "Rich Contrast" },
        { name: "Heather Taupe", hex: "#78716C", text: "Soft Tonal" },
      ];
    } else if (hips - waist > 18 && chest - waist > 16) {
      archetype = "Harmonic Hourglass";
      summary = "Balanced chest and hip contours with distinct waist definition.";
      stylingAdvice = "Bias-cut dresses, wrap silhouettes, belted trench coats, and high-rise trousers accentuate your natural waistline seamlessly.";
      colorPalette = [
        { name: "Warm Amber", hex: "#C29B38", text: "Radiant Waist" },
        { name: "Cognac Leather", hex: "#AD7E4A", text: "Curved Luxury" },
        { name: "Oatmeal Cream", hex: "#F5F5F4", text: "Soft Drapery" },
        { name: "Dark Bronze", hex: "#3B2F2F", text: "Fluid Depth" },
      ];
    } else if (hips - waist > 16 && chest - waist < 12) {
      archetype = "Graceful Triangle / Pear";
      summary = "Slender upper torso transitioning into broader hip and seat balance.";
      stylingAdvice = "A-line skirts, structured shoulder pads, boatneck collars, and statement lapels add balanced architectural presence to your upper frame.";
      colorPalette = [
        { name: "Cognac Camel", hex: "#AD7E4A", text: "Upper Focus" },
        { name: "Warm Ivory", hex: "#FAF7F2", text: "Torso Pop" },
        { name: "Deep Charcoal", hex: "#292524", text: "Slimming Base" },
        { name: "Champagne Gold", hex: "#D4AF37", text: "Warm Accent" },
      ];
    } else if (Math.abs(chest - hips) < 8 && Math.abs(chest - waist) < 14) {
      archetype = "Balanced Rectangular";
      summary = "Even athletic alignment across shoulders, chest, and hips.";
      stylingAdvice = "Pleated trousers, double-breasted blazers, and textured fabrics introduce dimensional depth and dynamic visual volume.";
      colorPalette = [
        { name: "Caramel Toffee", hex: "#AD7E4A", text: "Volume Warmth" },
        { name: "Ecru Linen", hex: "#FAF7F2", text: "Layered Light" },
        { name: "Warm Slate", hex: "#44403C", text: "Structured Frame" },
        { name: "Golden Sand", hex: "#C29B38", text: "Textured Earth" },
      ];
    }

    return {
      archetype,
      summary,
      stylingAdvice,
      colorPalette,
      chestWaistDrop,
      waistHipRatio: waistHipRatio.toFixed(2),
      shoulderWaistRatio: shoulderWaistRatio.toFixed(2),
    };
  }, [measurements]);

  // Multi-Standard International Sizing Computations
  const computedSizes = useMemo(() => {
    const { chest, waist, hips, inseam } = measurements;

    // Dress Size (US, UK, EU, IT, JP)
    let dressUS = "6 (S)";
    let dressUK = "10 (M)";
    let dressEU = "38 (M)";
    let dressIT = "42";
    let dressJP = "9";

    if (chest < 84 && waist < 66) {
      dressUS = "0–2 (XS)";
      dressUK = "4–6 (XS)";
      dressEU = "32–34 (XS)";
      dressIT = "36–38";
      dressJP = "5–7";
    } else if (chest < 90 && waist < 72) {
      dressUS = "4 (S)";
      dressUK = "8 (S)";
      dressEU = "36 (S)";
      dressIT = "40";
      dressJP = "7–9";
    } else if (chest < 96 && waist < 78) {
      dressUS = "6–8 (M)";
      dressUK = "10–12 (M)";
      dressEU = "38–40 (M)";
      dressIT = "42–44";
      dressJP = "11";
    } else if (chest < 104 && waist < 86) {
      dressUS = "10–12 (L)";
      dressUK = "14–16 (L)";
      dressEU = "42–44 (L)";
      dressIT = "46–48";
      dressJP = "13–15";
    } else {
      dressUS = "14–16 (XL)";
      dressUK = "18–20 (XL)";
      dressEU = "46–48 (XL)";
      dressIT = "50–52";
      dressJP = "17+";
    }

    // Tops, Shirts & Sweaters
    let topLetter = "M";
    if (chest < 88) topLetter = "XS";
    else if (chest < 94) topLetter = "S";
    else if (chest < 102) topLetter = "M";
    else if (chest < 110) topLetter = "L";
    else if (chest < 118) topLetter = "XL";
    else topLetter = "XXL";

    // Denim & Pants Waist (in inches) × Inseam (in inches)
    const waistInches = Math.round(waist / 2.54);
    const inseamInches = Math.round(inseam / 2.54);
    const pantsTag = `W${waistInches} × L${inseamInches}`;

    // Tailored Blazer / Overcoat
    const chestInches = Math.round(chest / 2.54);
    const heightInches = measurements.height / 2.54;
    const lengthLetter = heightInches < 67 ? "S" : heightInches > 73 ? "L" : "R";
    const jacketTag = `${chestInches}${lengthLetter}`;

    // Shoe Sizes
    const shoeEU = measurements.shoeSizeEU;
    const shoeUS = (shoeEU - 33).toFixed(1);
    const shoeUK = (shoeEU - 34).toFixed(1);

    return {
      dressUS,
      dressUK,
      dressEU,
      dressIT,
      dressJP,
      topLetter,
      pantsTag,
      jacketTag,
      shoeEU,
      shoeUS,
      shoeUK,
    };
  }, [measurements]);

  // Save to localStorage & notify engines
  const handleSave = () => {
    localStorage.setItem("verdict_user_measurements", JSON.stringify(measurements));
    if (typeof window !== "undefined") {
      window.dispatchEvent(new Event("verdict_measurements_updated"));
    }
    setSaveSuccess(true);
    setTimeout(() => setSaveSuccess(false), 3000);
  };

  // Reset to Defaults
  const handleReset = () => {
    setMeasurements(DEFAULT_MEASUREMENTS);
    localStorage.setItem("verdict_user_measurements", JSON.stringify(DEFAULT_MEASUREMENTS));
    setSaveSuccess(false);
  };

  // Export Measurement Dossier JSON
  const handleExport = () => {
    const data = {
      profile: "Verdict Luxury Body Measurements Dossier",
      exportedAt: new Date().toISOString(),
      measurements,
      silhouette: bodyShapeAnalysis,
      internationalSizes: computedSizes,
    };
    const blob = new Blob([JSON.stringify(data, null, 2)], { type: "application/json" });
    const url = URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = `verdict-body-profile-${measurements.fitPreference}.json`;
    link.click();
    URL.revokeObjectURL(url);
    setExportSuccess(true);
    setTimeout(() => setExportSuccess(false), 3000);
  };

  // Apply Preset Archetype
  const handleApplyPreset = (presetValues: Partial<UserBodyMeasurements>) => {
    setMeasurements((prev) => ({ ...prev, ...presetValues }));
  };

  return (
    <div className="min-h-screen flex flex-col bg-background text-foreground transition-colors duration-200">
      <NavigationHeader currentSubtitle="Body Measurements & Sizing Studio" badgeText="Fit Profile" />

      {/* EXPANSIVE WIDESCREEN CONTAINER — NO EMPTY SIDES, PURE BROWN & WHITE LUXURY PALETTE */}
      <main className="w-full flex-1 py-8 px-4 sm:px-6 lg:px-10 xl:px-14 max-w-[1780px] 2xl:max-w-[1920px] mx-auto space-y-8">
        {/* Header Hero Banner in Warm Cognac Brown & White Palette */}
        <div className="relative overflow-hidden rounded-3xl border border-amber-600/30 bg-gradient-to-r from-amber-600/10 via-card to-amber-600/5 p-6 sm:p-8 backdrop-blur-md shadow-sm">
          <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-6">
            <div className="space-y-2 max-w-4xl">
              <div className="flex flex-wrap items-center gap-2.5">
                <Badge className="bg-amber-600/15 text-amber-800 dark:text-amber-200 border-amber-600/30 text-xs font-bold px-3 py-1">
                  <Sparkles className="h-3.5 w-3.5 mr-1 text-amber-600" />
                  Anatomical Tailoring & Personal Sizing Architecture
                </Badge>
                <Badge variant="outline" className="border-border text-muted-foreground text-xs font-semibold">
                  Zero Hallucination Fit Engine
                </Badge>
              </div>
              <h1 className="text-3xl sm:text-5xl font-serif font-black tracking-tight text-foreground leading-tight">
                Body Measurements & Sizing Profile
              </h1>
              <p className="text-xs sm:text-sm text-muted-foreground leading-relaxed">
                Set and calibrate your complete anatomical proportions. The Verdict Decision Engine, What-If Cart Optimizer, and AI Stylist use these dimensions to audit candidate drape tension, calculate return risks, and recommend precise international sizes.
              </p>
            </div>

            <div className="flex flex-wrap items-center gap-3 shrink-0">
              {/* Metric / Imperial toggle */}
              <div className="p-1 rounded-2xl bg-muted/60 border border-border flex items-center gap-1 shadow-xs">
                <button
                  onClick={() => setUnit("cm")}
                  className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                    unit === "cm"
                      ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 shadow-xs"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Metric (cm)
                </button>
                <button
                  onClick={() => setUnit("in")}
                  className={`px-3.5 py-2 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                    unit === "in"
                      ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 shadow-xs"
                      : "text-muted-foreground hover:text-foreground"
                  }`}
                >
                  Imperial (in)
                </button>
              </div>

              {/* Save Button */}
              <Button
                onClick={handleSave}
                size="lg"
                className="h-11 px-5 rounded-2xl font-bold text-xs bg-amber-600 hover:bg-amber-700 text-white shadow-md gap-2 cursor-pointer transition-transform hover:scale-[1.02]"
              >
                <CheckCircle2 className="h-4 w-4" />
                <span>{saveSuccess ? "Profile Saved!" : "Save Dimensions"}</span>
              </Button>

              {/* Export Button */}
              <Button
                variant="outline"
                size="lg"
                onClick={handleExport}
                title="Download Measurement Dossier JSON"
                className="h-11 px-4 rounded-2xl font-bold text-xs gap-2 cursor-pointer border-border hover:bg-muted/40"
              >
                <Download className="h-4 w-4 text-muted-foreground" />
                <span>{exportSuccess ? "Exported!" : "Export"}</span>
              </Button>

              {/* Reset */}
              <Button
                variant="ghost"
                size="lg"
                onClick={handleReset}
                title="Reset to Defaults"
                className="h-11 px-3 rounded-2xl font-semibold text-xs text-muted-foreground hover:text-foreground cursor-pointer"
              >
                <RotateCcw className="h-4 w-4" />
              </Button>
            </div>
          </div>
        </div>

        {/* View Mode Navigation Tabs in Warm Brown & White */}
        <div className="flex items-center gap-2 border-b border-border/60 pb-3">
          <button
            onClick={() => setActiveTab("profile")}
            className={`px-5 py-2.5 rounded-2xl text-xs sm:text-sm font-bold transition-all cursor-pointer flex items-center gap-2 ${
              activeTab === "profile"
                ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
            }`}
          >
            <Sliders className="h-4 w-4 text-amber-600 dark:text-amber-400" />
            <span>Body Dimensions & Sliders</span>
          </button>

          <button
            onClick={() => setActiveTab("sizematrix")}
            className={`px-5 py-2.5 rounded-2xl text-xs sm:text-sm font-bold transition-all cursor-pointer flex items-center gap-2 ${
              activeTab === "sizematrix"
                ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
            }`}
          >
            <Layers className="h-4 w-4 text-amber-600 dark:text-amber-400" />
            <span>Universal Size Matrix</span>
          </button>

          <button
            onClick={() => setActiveTab("guidelines")}
            className={`px-5 py-2.5 rounded-2xl text-xs sm:text-sm font-bold transition-all cursor-pointer flex items-center gap-2 ${
              activeTab === "guidelines"
                ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 shadow-sm"
                : "text-muted-foreground hover:text-foreground hover:bg-muted/40"
            }`}
          >
            <HelpCircle className="h-4 w-4 text-amber-600 dark:text-amber-400" />
            <span>Measuring Guidelines</span>
          </button>
        </div>

        {/* TAB 1: BODY PROFILE & MEASUREMENT SLIDERS */}
        {activeTab === "profile" && (
          <div className="space-y-8">
            {/* Quick Fill Archetype Presets in Clean Brown & White Style */}
            <div className="p-5 rounded-3xl border border-amber-600/30 bg-amber-600/5 shadow-sm space-y-3">
              <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-2">
                <span className="text-xs font-bold uppercase tracking-wider text-amber-800 dark:text-amber-300 flex items-center gap-2">
                  <Sparkles className="h-4 w-4 text-amber-600" />
                  Quick Fill Starting Archetype:
                </span>
                <span className="text-[11px] text-muted-foreground">
                  Click any archetype to populate starting dimensions, then customize individual sliders below
                </span>
              </div>

              <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-3.5">
                {ARCHETYPE_PRESETS.map((p) => (
                  <button
                    key={p.name}
                    onClick={() => handleApplyPreset(p.values)}
                    className="p-4 rounded-2xl border border-border/80 bg-card hover:border-amber-600/50 hover:bg-amber-600/5 transition-all text-left cursor-pointer space-y-2 shadow-xs group hover:scale-[1.01]"
                  >
                    <div className="flex items-center justify-between">
                      <p className="font-bold text-xs sm:text-sm text-foreground truncate">{p.label}</p>
                      <span className="text-[10px] font-bold px-2 py-0.5 rounded-full border border-amber-600/30 bg-amber-600/10 text-amber-800 dark:text-amber-200">
                        {p.tag}
                      </span>
                    </div>
                    <p className="text-[11px] text-muted-foreground line-clamp-2 leading-relaxed">
                      {p.desc}
                    </p>
                  </button>
                ))}
              </div>
            </div>

            {/* EXPANSIVE WIDESCREEN GRID: 8 COLS INPUTS | 4 COLS LIVE SILHOUETTE CARD */}
            <div className="grid grid-cols-1 lg:grid-cols-12 gap-8 items-start">
              {/* LEFT & CENTER: INPUT SECTIONS (8 cols) — WARM BROWN & WHITE STYLING */}
              <div className="lg:col-span-8 space-y-6">
                {/* 1. Stature & Vertical Lengths */}
                <Card className="border border-border/80 bg-card rounded-3xl shadow-sm overflow-hidden hover:border-amber-600/30 transition-colors">
                  <CardHeader className="pb-3 border-b border-border/60 bg-muted/10">
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-2.5 text-base font-serif font-bold text-foreground">
                        <div className="p-1.5 rounded-xl bg-amber-600/10 text-amber-700 dark:text-amber-300">
                          <Ruler className="h-4 w-4" />
                        </div>
                        <span>1. Stature & Vertical Proportions</span>
                      </CardTitle>
                      <Badge className="bg-amber-600/15 text-amber-800 dark:text-amber-200 border-amber-600/30 text-[10px] font-bold">
                        Stature
                      </Badge>
                    </div>
                    <CardDescription className="text-xs text-muted-foreground">
                      Total standing height, torso length, and leg inseam clearance for garment drop.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-6 space-y-6">
                    {/* Height */}
                    <div className="space-y-2">
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-bold text-foreground">Total Standing Height</span>
                        <span className="font-mono font-bold text-sm text-amber-800 dark:text-amber-300 bg-amber-600/10 px-2.5 py-0.5 rounded-lg border border-amber-600/20">
                          {toDisplay(measurements.height)}
                        </span>
                      </div>
                      <input
                        type="range"
                        min="145"
                        max="215"
                        step="1"
                        value={measurements.height}
                        onChange={(e) => setMeasurements({ ...measurements, height: parseFloat(e.target.value) })}
                        className="w-full accent-neutral-900 dark:accent-white cursor-pointer h-2 bg-muted rounded-lg"
                      />
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-2">
                      {/* Inseam */}
                      <div className="space-y-2">
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-bold text-foreground">Inseam (Crotch to Ankle)</span>
                          <span className="font-mono font-bold text-foreground bg-muted/60 px-2 py-0.5 rounded-lg">
                            {toDisplay(measurements.inseam)}
                          </span>
                        </div>
                        <input
                          type="range"
                          min="62"
                          max="96"
                          step="0.5"
                          value={measurements.inseam}
                          onChange={(e) => setMeasurements({ ...measurements, inseam: parseFloat(e.target.value) })}
                          className="w-full accent-neutral-900 dark:accent-white cursor-pointer h-2 bg-muted rounded-lg"
                        />
                      </div>

                      {/* Torso Length */}
                      <div className="space-y-2">
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-bold text-foreground">Torso / Back Length</span>
                          <span className="font-mono font-bold text-foreground bg-muted/60 px-2 py-0.5 rounded-lg">
                            {toDisplay(measurements.torsoLength)}
                          </span>
                        </div>
                        <input
                          type="range"
                          min="35"
                          max="58"
                          step="0.5"
                          value={measurements.torsoLength}
                          onChange={(e) => setMeasurements({ ...measurements, torsoLength: parseFloat(e.target.value) })}
                          className="w-full accent-neutral-900 dark:accent-white cursor-pointer h-2 bg-muted rounded-lg"
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* 2. Upper Body: Bust, Shoulders, Arms, Neck */}
                <Card className="border border-border/80 bg-card rounded-3xl shadow-sm overflow-hidden hover:border-amber-600/30 transition-colors">
                  <CardHeader className="pb-3 border-b border-border/60 bg-muted/10">
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-2.5 text-base font-serif font-bold text-foreground">
                        <div className="p-1.5 rounded-xl bg-amber-600/10 text-amber-700 dark:text-amber-300">
                          <Shirt className="h-4 w-4" />
                        </div>
                        <span>2. Upper Body (Chest, Shoulders & Arms)</span>
                      </CardTitle>
                      <Badge className="bg-amber-600/15 text-amber-800 dark:text-amber-200 border-amber-600/30 text-[10px] font-bold">
                        Upper Torso
                      </Badge>
                    </div>
                    <CardDescription className="text-xs text-muted-foreground">
                      Chest circumference, shoulder span, neck collar, and sleeve reach for blouses and blazers.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-6 space-y-6">
                    {/* Chest / Bust */}
                    <div className="space-y-2">
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-bold text-foreground">Chest / Full Bust Circumference</span>
                        <span className="font-mono font-bold text-sm text-amber-800 dark:text-amber-300 bg-amber-600/10 px-2.5 py-0.5 rounded-lg border border-amber-600/20">
                          {toDisplay(measurements.chest)}
                        </span>
                      </div>
                      <input
                        type="range"
                        min="70"
                        max="140"
                        step="1"
                        value={measurements.chest}
                        onChange={(e) => setMeasurements({ ...measurements, chest: parseFloat(e.target.value) })}
                        className="w-full accent-neutral-900 dark:accent-white cursor-pointer h-2 bg-muted rounded-lg"
                      />
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-2 gap-6 pt-2">
                      {/* Underbust */}
                      <div className="space-y-2">
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-bold text-foreground">Underbust Band</span>
                          <span className="font-mono font-bold text-foreground bg-muted/60 px-2 py-0.5 rounded-lg">
                            {toDisplay(measurements.underbust)}
                          </span>
                        </div>
                        <input
                          type="range"
                          min="60"
                          max="120"
                          step="1"
                          value={measurements.underbust}
                          onChange={(e) => setMeasurements({ ...measurements, underbust: parseFloat(e.target.value) })}
                          className="w-full accent-neutral-900 dark:accent-white cursor-pointer h-2 bg-muted rounded-lg"
                        />
                      </div>

                      {/* Shoulder Width */}
                      <div className="space-y-2">
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-bold text-foreground">Bi-Acromial Shoulder Width</span>
                          <span className="font-mono font-bold text-foreground bg-muted/60 px-2 py-0.5 rounded-lg">
                            {toDisplay(measurements.shoulders)}
                          </span>
                        </div>
                        <input
                          type="range"
                          min="34"
                          max="58"
                          step="0.5"
                          value={measurements.shoulders}
                          onChange={(e) => setMeasurements({ ...measurements, shoulders: parseFloat(e.target.value) })}
                          className="w-full accent-neutral-900 dark:accent-white cursor-pointer h-2 bg-muted rounded-lg"
                        />
                      </div>

                      {/* Arm Length */}
                      <div className="space-y-2">
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-bold text-foreground">Arm / Sleeve Length</span>
                          <span className="font-mono font-bold text-foreground bg-muted/60 px-2 py-0.5 rounded-lg">
                            {toDisplay(measurements.armLength)}
                          </span>
                        </div>
                        <input
                          type="range"
                          min="48"
                          max="75"
                          step="0.5"
                          value={measurements.armLength}
                          onChange={(e) => setMeasurements({ ...measurements, armLength: parseFloat(e.target.value) })}
                          className="w-full accent-neutral-900 dark:accent-white cursor-pointer h-2 bg-muted rounded-lg"
                        />
                      </div>

                      {/* Neck Circumference */}
                      <div className="space-y-2">
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-bold text-foreground">Neck Collar Circumference</span>
                          <span className="font-mono font-bold text-foreground bg-muted/60 px-2 py-0.5 rounded-lg">
                            {toDisplay(measurements.neck)}
                          </span>
                        </div>
                        <input
                          type="range"
                          min="30"
                          max="50"
                          step="0.5"
                          value={measurements.neck}
                          onChange={(e) => setMeasurements({ ...measurements, neck: parseFloat(e.target.value) })}
                          className="w-full accent-neutral-900 dark:accent-white cursor-pointer h-2 bg-muted rounded-lg"
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* 3. Core & Lower Body: Waist, Hips & Thighs */}
                <Card className="border border-border/80 bg-card rounded-3xl shadow-sm overflow-hidden hover:border-amber-600/30 transition-colors">
                  <CardHeader className="pb-3 border-b border-border/60 bg-muted/10">
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-2.5 text-base font-serif font-bold text-foreground">
                        <div className="p-1.5 rounded-xl bg-amber-600/10 text-amber-700 dark:text-amber-300">
                          <Scissors className="h-4 w-4" />
                        </div>
                        <span>3. Core & Lower Body (Waist, Hips & Thighs)</span>
                      </CardTitle>
                      <Badge className="bg-amber-600/15 text-amber-800 dark:text-amber-200 border-amber-600/30 text-[10px] font-bold">
                        Lower Silhouette
                      </Badge>
                    </div>
                    <CardDescription className="text-xs text-muted-foreground">
                      Natural indentation waist, iliac crest, full gluteal seat, and upper thigh contours.
                    </CardDescription>
                  </CardHeader>
                  <CardContent className="p-6 space-y-6">
                    {/* Natural Waist */}
                    <div className="space-y-2">
                      <div className="flex justify-between items-center text-xs">
                        <span className="font-bold text-foreground">Natural Waist (Narrowest Point)</span>
                        <span className="font-mono font-bold text-sm text-amber-800 dark:text-amber-300 bg-amber-600/10 px-2.5 py-0.5 rounded-lg border border-amber-600/20">
                          {toDisplay(measurements.waist)}
                        </span>
                      </div>
                      <input
                        type="range"
                        min="58"
                        max="130"
                        step="1"
                        value={measurements.waist}
                        onChange={(e) => setMeasurements({ ...measurements, waist: parseFloat(e.target.value) })}
                        className="w-full accent-neutral-900 dark:accent-white cursor-pointer h-2 bg-muted rounded-lg"
                      />
                    </div>

                    <div className="grid grid-cols-1 sm:grid-cols-3 gap-6 pt-2">
                      {/* High Hip */}
                      <div className="space-y-2">
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-bold text-foreground">High Hip (Bone)</span>
                          <span className="font-mono font-bold text-foreground bg-muted/60 px-2 py-0.5 rounded-lg">
                            {toDisplay(measurements.highHip)}
                          </span>
                        </div>
                        <input
                          type="range"
                          min="68"
                          max="135"
                          step="1"
                          value={measurements.highHip}
                          onChange={(e) => setMeasurements({ ...measurements, highHip: parseFloat(e.target.value) })}
                          className="w-full accent-neutral-900 dark:accent-white cursor-pointer h-2 bg-muted rounded-lg"
                        />
                      </div>

                      {/* Full Hips / Seat */}
                      <div className="space-y-2">
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-bold text-foreground">Hips / Seat (Widest)</span>
                          <span className="font-mono font-bold text-foreground bg-muted/60 px-2 py-0.5 rounded-lg">
                            {toDisplay(measurements.hips)}
                          </span>
                        </div>
                        <input
                          type="range"
                          min="75"
                          max="145"
                          step="1"
                          value={measurements.hips}
                          onChange={(e) => setMeasurements({ ...measurements, hips: parseFloat(e.target.value) })}
                          className="w-full accent-neutral-900 dark:accent-white cursor-pointer h-2 bg-muted rounded-lg"
                        />
                      </div>

                      {/* Thigh */}
                      <div className="space-y-2">
                        <div className="flex justify-between items-center text-xs">
                          <span className="font-bold text-foreground">Thigh Circumference</span>
                          <span className="font-mono font-bold text-foreground bg-muted/60 px-2 py-0.5 rounded-lg">
                            {toDisplay(measurements.thigh)}
                          </span>
                        </div>
                        <input
                          type="range"
                          min="40"
                          max="80"
                          step="0.5"
                          value={measurements.thigh}
                          onChange={(e) => setMeasurements({ ...measurements, thigh: parseFloat(e.target.value) })}
                          className="w-full accent-neutral-900 dark:accent-white cursor-pointer h-2 bg-muted rounded-lg"
                        />
                      </div>
                    </div>
                  </CardContent>
                </Card>

                {/* 4. Fit Preferences & Footwear */}
                <Card className="border border-border/80 bg-card rounded-3xl shadow-sm overflow-hidden hover:border-amber-600/30 transition-colors">
                  <CardHeader className="pb-3 border-b border-border/60 bg-muted/10">
                    <div className="flex items-center justify-between">
                      <CardTitle className="flex items-center gap-2.5 text-base font-serif font-bold text-foreground">
                        <div className="p-1.5 rounded-xl bg-amber-600/10 text-amber-700 dark:text-amber-300">
                          <Layers className="h-4 w-4" />
                        </div>
                        <span>4. Fit Preference & Footwear Calibration</span>
                      </CardTitle>
                      <Badge className="bg-amber-600/15 text-amber-800 dark:text-amber-200 border-amber-600/30 text-[10px] font-bold">
                        Ease Margin
                      </Badge>
                    </div>
                  </CardHeader>
                  <CardContent className="p-6 space-y-6">
                    {/* Fit Preference Button Grid */}
                    <div className="space-y-2.5">
                      <label className="text-xs font-bold text-foreground block">
                        Preferred Garment Ease & Drape Margin
                      </label>
                      <div className="grid grid-cols-2 sm:grid-cols-4 gap-2.5">
                        {[
                          { id: "slim", label: "Slim Contour", desc: "Body-skimming fit" },
                          { id: "tailored", label: "Tailored Classic", desc: "Clean drape with 3cm ease" },
                          { id: "relaxed", label: "Relaxed Drape", desc: "Effortless airflow ease" },
                          { id: "oversized", label: "Oversized Editorial", desc: "Volumetric high-fashion" },
                        ].map((p) => (
                          <button
                            key={p.id}
                            onClick={() => setMeasurements({ ...measurements, fitPreference: p.id as any })}
                            className={`p-3.5 rounded-2xl border text-left transition-all cursor-pointer ${
                              measurements.fitPreference === p.id
                                ? "border-amber-600 bg-amber-600/15 text-amber-900 dark:text-amber-100 shadow-sm font-bold scale-[1.01]"
                                : "border-border/80 hover:bg-muted/40 text-foreground bg-card"
                            }`}
                          >
                            <p className="text-xs font-bold">{p.label}</p>
                            <p className="text-[10px] mt-0.5 text-muted-foreground">
                              {p.desc}
                            </p>
                          </button>
                        ))}
                      </div>
                    </div>

                    {/* Shoe Size */}
                    <div className="pt-2 border-t border-border/60 flex flex-col sm:flex-row sm:items-center justify-between gap-4">
                      <div>
                        <span className="text-xs font-bold text-foreground block">Footwear Size (EU)</span>
                        <span className="text-[11px] text-muted-foreground">
                          Corresponds to US {computedSizes.shoeUS} · UK {computedSizes.shoeUK}
                        </span>
                      </div>
                      <div className="flex flex-wrap items-center gap-1.5">
                        {[37, 38, 39, 40, 41, 42, 43, 44, 45].map((s) => (
                          <button
                            key={s}
                            onClick={() => setMeasurements({ ...measurements, shoeSizeEU: s })}
                            className={`h-9 w-9 rounded-xl text-xs font-bold transition-all cursor-pointer ${
                              measurements.shoeSizeEU === s
                                ? "bg-amber-600 text-white shadow-sm scale-105"
                                : "bg-muted/50 text-muted-foreground hover:text-foreground"
                            }`}
                          >
                            {s}
                          </button>
                        ))}
                      </div>
                    </div>
                  </CardContent>
                </Card>
              </div>

              {/* RIGHT: ARCHITECTURAL PROPORTION & SUMMARY CARD (4 cols) — COGNAC BROWN & WHITE */}
              <div className="lg:col-span-4 space-y-6">
                <Card className="border-2 border-amber-600/30 bg-card rounded-3xl shadow-md overflow-hidden sticky top-24">
                  <div className="p-6 bg-gradient-to-br from-amber-600/15 via-amber-700/5 to-transparent border-b border-amber-600/20">
                    <div className="space-y-1.5">
                      <span className="text-[10px] font-bold uppercase tracking-wider text-amber-800 dark:text-amber-300 block">
                        Calculated Body Silhouette Archetype
                      </span>
                      <h2 className="text-2xl sm:text-3xl font-serif font-black tracking-tight text-foreground">
                        {bodyShapeAnalysis.archetype}
                      </h2>
                      <p className="text-xs text-muted-foreground leading-relaxed pt-1">
                        {bodyShapeAnalysis.summary}
                      </p>
                    </div>
                  </div>

                  <CardContent className="p-6 space-y-6">
                    {/* Proportion Telemetry */}
                    <div className="space-y-3">
                      <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
                        Proportion Telemetry
                      </span>
                      <div className="grid grid-cols-2 gap-2.5 text-xs">
                        <div className="p-3 rounded-2xl border border-border/80 bg-muted/20 space-y-0.5">
                          <span className="text-[10px] text-muted-foreground block uppercase font-bold">Waist-to-Hip</span>
                          <span className="text-lg font-black font-mono text-foreground">
                            {bodyShapeAnalysis.waistHipRatio}
                          </span>
                        </div>

                        <div className="p-3 rounded-2xl border border-border/80 bg-muted/20 space-y-0.5">
                          <span className="text-[10px] text-muted-foreground block uppercase font-bold">Chest-Waist Drop</span>
                          <span className="text-lg font-black font-mono text-foreground">
                            {toDisplay(bodyShapeAnalysis.chestWaistDrop)}
                          </span>
                        </div>

                        <div className="p-3 rounded-2xl border border-border/80 bg-muted/20 space-y-0.5">
                          <span className="text-[10px] text-muted-foreground block uppercase font-bold">Shoulder-Waist</span>
                          <span className="text-lg font-black font-mono text-foreground">
                            {bodyShapeAnalysis.shoulderWaistRatio}x
                          </span>
                        </div>

                        <div className="p-3 rounded-2xl border border-amber-600/30 bg-amber-600/10 space-y-0.5">
                          <span className="text-[10px] text-amber-800 dark:text-amber-300 block uppercase font-bold">Fit Margin</span>
                          <span className="text-lg font-black font-serif text-amber-800 dark:text-amber-200 capitalize">
                            {measurements.fitPreference}
                          </span>
                        </div>
                      </div>
                    </div>

                    {/* Calculated Size Matrix Badges */}
                    <div className="space-y-2.5 pt-2 border-t border-border/60">
                      <span className="text-xs font-bold uppercase tracking-wider text-muted-foreground block">
                        Calculated Size Matrix
                      </span>
                      <div className="space-y-2">
                        <div className="flex items-center justify-between p-3 rounded-2xl border bg-card hover:bg-muted/20 transition-colors">
                          <span className="text-xs font-bold text-foreground">Dresses & Gowns</span>
                          <Badge variant="outline" className="border-amber-600/40 text-amber-800 dark:text-amber-200 font-black text-xs">
                            US {computedSizes.dressUS}
                          </Badge>
                        </div>

                        <div className="flex items-center justify-between p-3 rounded-2xl border bg-card hover:bg-muted/20 transition-colors">
                          <span className="text-xs font-bold text-foreground">Tops & Knitwear</span>
                          <Badge variant="outline" className="border-amber-600/40 text-amber-800 dark:text-amber-200 font-black text-xs">
                            {computedSizes.topLetter}
                          </Badge>
                        </div>

                        <div className="flex items-center justify-between p-3 rounded-2xl border bg-card hover:bg-muted/20 transition-colors">
                          <span className="text-xs font-bold text-foreground">Pants & Denim</span>
                          <Badge variant="outline" className="border-amber-600/40 text-amber-800 dark:text-amber-200 font-black text-xs font-mono">
                            {computedSizes.pantsTag}
                          </Badge>
                        </div>

                        <div className="flex items-center justify-between p-3 rounded-2xl border bg-card hover:bg-muted/20 transition-colors">
                          <span className="text-xs font-bold text-foreground">Tailored Blazer</span>
                          <Badge variant="outline" className="border-amber-600/40 text-amber-800 dark:text-amber-200 font-black text-xs font-mono">
                            {computedSizes.jacketTag}
                          </Badge>
                        </div>
                      </div>
                    </div>

                    {/* Color Harmony Recommendations in Classic Tones */}
                    <div className="space-y-2 pt-2 border-t border-border/60">
                      <div className="flex items-center gap-1.5 text-xs font-bold text-muted-foreground uppercase tracking-wider">
                        <Palette className="h-3.5 w-3.5 text-amber-600" />
                        <span>Harmonic Color Palette</span>
                      </div>
                      <div className="grid grid-cols-2 gap-2">
                        {bodyShapeAnalysis.colorPalette.map((col, idx) => (
                          <div key={idx} className="flex items-center gap-2 p-2 rounded-xl border bg-muted/20">
                            <div className="h-5 w-5 rounded-lg border shadow-2xs shrink-0" style={{ backgroundColor: col.hex }} />
                            <div className="min-w-0">
                              <p className="text-[11px] font-bold text-foreground truncate">{col.name}</p>
                              <p className="text-[9px] text-muted-foreground truncate">{col.text}</p>
                            </div>
                          </div>
                        ))}
                      </div>
                    </div>

                    {/* Architectural Styling Directive */}
                    <div className="p-4 rounded-2xl border border-amber-600/30 bg-amber-600/5 space-y-1.5">
                      <div className="flex items-center gap-2 text-xs font-bold text-amber-800 dark:text-amber-300">
                        <Sparkles className="h-4 w-4 text-amber-600" />
                        <span>Stylist Directive</span>
                      </div>
                      <p className="text-xs text-muted-foreground leading-relaxed">
                        {bodyShapeAnalysis.stylingAdvice}
                      </p>
                    </div>

                    {/* Save Button in Sidebar */}
                    <Button
                      onClick={handleSave}
                      size="lg"
                      className="w-full h-11 text-xs sm:text-sm font-bold bg-neutral-900 text-white hover:bg-black dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-100 rounded-2xl shadow-md gap-2 cursor-pointer transition-transform hover:scale-[1.01]"
                    >
                      <CheckCircle2 className="h-4 w-4" />
                      <span>{saveSuccess ? "Measurements Saved!" : "Save Dimensions"}</span>
                    </Button>
                  </CardContent>
                </Card>
              </div>
            </div>
          </div>
        )}

        {/* TAB 2: UNIVERSAL MULTI-COUNTRY SIZE MATRIX */}
        {activeTab === "sizematrix" && (
          <div className="space-y-6">
            <Card className="border border-border/80 bg-card rounded-3xl shadow-sm overflow-hidden">
              <CardHeader className="pb-4 border-b border-border/60 bg-muted/10">
                <CardTitle className="text-xl sm:text-2xl font-serif font-bold text-foreground">
                  Universal Multi-Country Sizing Matrix
                </CardTitle>
                <CardDescription className="text-xs text-muted-foreground">
                  Computed live based on your body dimensions (Height: {toDisplay(measurements.height)}, Chest: {toDisplay(measurements.chest)}, Waist: {toDisplay(measurements.waist)}, Hips: {toDisplay(measurements.hips)}).
                </CardDescription>
              </CardHeader>
              <CardContent className="p-6 sm:p-8 space-y-6">
                <div className="overflow-x-auto">
                  <table className="w-full text-left border-collapse text-xs sm:text-sm">
                    <thead>
                      <tr className="border-b border-border/80 bg-muted/20">
                        <th className="py-3.5 px-4 font-bold uppercase text-[11px] text-muted-foreground">Garment Category</th>
                        <th className="py-3.5 px-4 font-bold uppercase text-[11px] text-amber-800 dark:text-amber-300">United States (US)</th>
                        <th className="py-3.5 px-4 font-bold uppercase text-[11px] text-muted-foreground">United Kingdom (UK)</th>
                        <th className="py-3.5 px-4 font-bold uppercase text-[11px] text-muted-foreground">Europe (EU)</th>
                        <th className="py-3.5 px-4 font-bold uppercase text-[11px] text-muted-foreground">Italy (IT)</th>
                        <th className="py-3.5 px-4 font-bold uppercase text-[11px] text-muted-foreground">Japan (JP)</th>
                      </tr>
                    </thead>
                    <tbody className="divide-y divide-border/60">
                      <tr className="hover:bg-muted/10 transition-colors">
                        <td className="py-4 px-4 font-bold text-foreground">Dresses & Eveningwear</td>
                        <td className="py-4 px-4 font-mono font-bold text-amber-800 dark:text-amber-300">{computedSizes.dressUS}</td>
                        <td className="py-4 px-4 font-mono font-bold text-foreground">{computedSizes.dressUK}</td>
                        <td className="py-4 px-4 font-mono font-bold text-foreground">{computedSizes.dressEU}</td>
                        <td className="py-4 px-4 font-mono font-bold text-foreground">{computedSizes.dressIT}</td>
                        <td className="py-4 px-4 font-mono font-bold text-foreground">{computedSizes.dressJP}</td>
                      </tr>

                      <tr className="hover:bg-muted/10 transition-colors">
                        <td className="py-4 px-4 font-bold text-foreground">Tops, Shirts & Knitwear</td>
                        <td className="py-4 px-4 font-mono font-bold text-amber-800 dark:text-amber-300">{computedSizes.topLetter}</td>
                        <td className="py-4 px-4 font-mono font-bold text-foreground">{computedSizes.topLetter}</td>
                        <td className="py-4 px-4 font-mono font-bold text-foreground">{computedSizes.topLetter} (EU {computedSizes.dressEU.split(" ")[0]})</td>
                        <td className="py-4 px-4 font-mono font-bold text-foreground">{computedSizes.dressIT}</td>
                        <td className="py-4 px-4 font-mono font-bold text-foreground">{computedSizes.dressJP}</td>
                      </tr>

                      <tr className="hover:bg-muted/10 transition-colors">
                        <td className="py-4 px-4 font-bold text-foreground">Pants & Denim</td>
                        <td className="py-4 px-4 font-mono font-bold text-amber-800 dark:text-amber-300">{computedSizes.pantsTag}</td>
                        <td className="py-4 px-4 font-mono font-bold text-foreground">{computedSizes.pantsTag}</td>
                        <td className="py-4 px-4 font-mono font-bold text-foreground">EU {Math.round(measurements.waist / 2)}</td>
                        <td className="py-4 px-4 font-mono font-bold text-foreground">IT {Math.round(measurements.waist / 2) + 4}</td>
                        <td className="py-4 px-4 font-mono font-bold text-foreground">JP {Math.round(measurements.waist / 2.54)}</td>
                      </tr>

                      <tr className="hover:bg-muted/10 transition-colors">
                        <td className="py-4 px-4 font-bold text-foreground">Tailored Blazer & Coats</td>
                        <td className="py-4 px-4 font-mono font-bold text-amber-800 dark:text-amber-300">{computedSizes.jacketTag}</td>
                        <td className="py-4 px-4 font-mono font-bold text-foreground">{computedSizes.jacketTag}</td>
                        <td className="py-4 px-4 font-mono font-bold text-foreground">EU {Math.round(measurements.chest / 2)}</td>
                        <td className="py-4 px-4 font-mono font-bold text-foreground">IT {Math.round(measurements.chest / 2) + 4}</td>
                        <td className="py-4 px-4 font-mono font-bold text-foreground">JP {computedSizes.topLetter}</td>
                      </tr>

                      <tr className="hover:bg-muted/10 transition-colors">
                        <td className="py-4 px-4 font-bold text-foreground">Footwear</td>
                        <td className="py-4 px-4 font-mono font-bold text-amber-800 dark:text-amber-300">US {computedSizes.shoeUS}</td>
                        <td className="py-4 px-4 font-mono font-bold text-foreground">UK {computedSizes.shoeUK}</td>
                        <td className="py-4 px-4 font-mono font-bold text-foreground">EU {computedSizes.shoeEU}</td>
                        <td className="py-4 px-4 font-mono font-bold text-foreground">IT {computedSizes.shoeEU}</td>
                        <td className="py-4 px-4 font-mono font-bold text-foreground">{(measurements.shoeSizeEU * 0.65).toFixed(1)} cm</td>
                      </tr>
                    </tbody>
                  </table>
                </div>

                <div className="p-4 rounded-2xl border border-amber-600/30 bg-amber-600/5 flex items-start gap-3">
                  <Info className="h-4 w-4 text-amber-700 dark:text-amber-400 shrink-0 mt-0.5" />
                  <p className="text-xs text-muted-foreground leading-relaxed">
                    <strong>Tailoring Tolerance: </strong>
                    Luxury designer houses (e.g. Italian and French labels) cut closer to the body contour. If you are shopping slim-cut Milanese tailoring or structured Parisian eveningwear, consider sizing up by 1 increment if you prefer relaxed drape.
                  </p>
                </div>
              </CardContent>
            </Card>
          </div>
        )}

        {/* TAB 3: ILLUSTRATED MEASURING GUIDELINES */}
        {activeTab === "guidelines" && (
          <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 gap-6">
            {[
              {
                title: "Chest / Bust",
                rule: "Fullest horizontal point",
                guide: "Keep the measuring tape comfortably snug but not constricting, passing directly under the armpits and across the fullest part of your shoulder blades and bust.",
              },
              {
                title: "Natural Waist",
                rule: "Narrowest torso indentation",
                guide: "Locate the crease that forms when bending to one side (typically 2 to 3 cm above your navel). Breathe out naturally and measure around this circumference.",
              },
              {
                title: "Hips & Seat",
                rule: "Widest gluteal point",
                guide: "Stand with heels together and wrap the tape around the fullest point of your hips and rear, keeping the measuring tape parallel to the floor.",
              },
              {
                title: "Shoulder Span",
                rule: "Bone tip to bone tip",
                guide: "Measure across the upper curvature of your back from the outermost prominent bone tip of the left shoulder to the right shoulder.",
              },
              {
                title: "Inseam Length",
                rule: "Crotch seam to ankle bone",
                guide: "Stand barefoot against a wall. Measure vertically along the inner leg seam from the highest point of the crotch down to the ankle bone.",
              },
              {
                title: "Arm / Sleeve Length",
                rule: "Shoulder point to wrist bone",
                guide: "Bend arm slightly at a 45° angle. Measure from the top tip of your shoulder down past the elbow to the prominent wrist bone.",
              },
            ].map((g, i) => (
              <Card key={i} className="border border-border/80 bg-card rounded-3xl p-6 shadow-sm space-y-3 hover:border-amber-600/40 transition-colors">
                <div className="flex items-center justify-between">
                  <span className="font-serif font-bold text-base text-foreground">{g.title}</span>
                  <span className="text-[10px] uppercase font-bold px-2 py-0.5 rounded-full border border-amber-600/30 bg-amber-600/10 text-amber-800 dark:text-amber-200">
                    {g.rule}
                  </span>
                </div>
                <p className="text-xs text-muted-foreground leading-relaxed pt-1">
                  {g.guide}
                </p>
              </Card>
            ))}
          </div>
        )}
      </main>
    </div>
  );
}
