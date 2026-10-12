"use client";

import React, { useEffect, useRef, useState } from "react";
import Link from "next/link";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  Send,
  Loader2,
  ShieldAlert,
  ShieldCheck,
  Shirt,
  Compass,
  LayoutDashboard,
  Layers,
  ArrowRight,
  Info,
  CheckCircle2,
  Bot,
  User as UserIcon,
  Palette,
  FolderHeart,
  Calendar,
  MessageSquare,
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle, CardDescription } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { NavigationHeader } from "@/components/NavigationHeader";
import { fadeUpVariants } from "@/lib/animations";
import {
  chatWithStylist,
  fetchWardrobe,
  type RetrievedWardrobeItemData,
  type StylistChatResponseData,
  type WardrobeItemData,
} from "@/lib/api";

interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  retrieved_items?: RetrievedWardrobeItemData[];
  provider_used?: string;
  model_used?: string;
  guardrail_triggered?: boolean;
  timestamp: string;
}

const STARTER_PROMPTS = [
  {
    title: "What goes with my dark jacket?",
    category: "Outfit Pairing",
    isGuardrailTest: false,
  },
  {
    title: "Suggest a smart-casual dinner outfit",
    category: "Occasion",
    isGuardrailTest: false,
  },
  {
    title: "Do I have versatile tops for layering?",
    category: "Versatility",
    isGuardrailTest: false,
  },
  {
    title: "Style my white crewneck tee",
    category: "Wardrobe Key Piece",
    isGuardrailTest: false,
  },
  {
    title: "What's trending in Paris fashion week?",
    category: "Guardrail Test",
    isGuardrailTest: true,
  },
];

export default function StylistChatPage() {
  return (
    <ProtectedRoute>
      <StylistChatContent />
    </ProtectedRoute>
  );
}

function StylistChatContent() {
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "welcome-msg",
      sender: "assistant",
      text: "Hello! I am Verdict Stylist. I evaluate outfit pairings and purchase decisions strictly grounded in what you actually own in your wardrobe. Ask me how to style your clothes or how a potential new item pairs with your closet.",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [input, setInput] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [wardrobeItems, setWardrobeItems] = useState<WardrobeItemData[]>([]);
  const [loadingWardrobe, setLoadingWardrobe] = useState<boolean>(true);
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

  // Load user's actual indexed wardrobe items on mount
  useEffect(() => {
    let isMounted = true;
    fetchWardrobe(40)
      .then((items) => {
        if (isMounted) setWardrobeItems(items);
      })
      .catch((err) => {
        console.warn("Could not load wardrobe items for stylist quick drawer:", err);
      })
      .finally(() => {
        if (isMounted) setLoadingWardrobe(false);
      });

    return () => {
      isMounted = false;
    };
  }, []);

  async function handleSend(textToSend?: string) {
    const query = (textToSend || input).trim();
    if (!query || isLoading) return;

    setError(null);
    setInput("");

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setIsLoading(true);

    try {
      const res: StylistChatResponseData = await chatWithStylist(query);

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: "assistant",
        text: res.reply,
        retrieved_items: res.retrieved_items,
        provider_used: res.provider_used,
        model_used: res.model_used,
        guardrail_triggered: res.guardrail_triggered,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      setError(err?.message || "Failed to communicate with Verdict Stylist. Please try again.");
    } finally {
      setIsLoading(false);
    }
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLInputElement>) {
    if (e.key === "Enter" && !e.shiftKey) {
      e.preventDefault();
      handleSend();
    }
  }

  function handleStyleWardrobeItem(item: WardrobeItemData) {
    const cat = item.attributes?.category || "piece";
    const col = item.attributes?.color ? `${item.attributes.color} ` : "";
    handleSend(`How should I style my ${col}${cat} (item #${item.id}) with the rest of my closet?`);
  }

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col transition-colors duration-200">
      <NavigationHeader currentSubtitle="Stylist Chat" badgeText="Grounded RAG" />

      {/* EXPANSIVE WIDESCREEN CONTAINER — NO SIDE WASTED SPACE, PURE BROWN & WHITE PALETTE */}
      <main className="w-full flex-1 py-8 px-4 sm:px-6 lg:px-10 xl:px-14 max-w-[1780px] 2xl:max-w-[1920px] mx-auto space-y-6 flex flex-col">
        {/* Header Hero Banner in Warm Cognac Brown & White Palette */}
        <div className="relative overflow-hidden rounded-3xl border border-amber-600/30 bg-gradient-to-r from-amber-600/10 via-card to-amber-600/5 p-6 sm:p-8 backdrop-blur-md shadow-sm">
          <div className="flex flex-col sm:flex-row sm:items-center justify-between gap-4">
            <div className="space-y-2">
              <div className="flex flex-wrap items-center gap-2">
                <Badge className="bg-amber-600/15 text-amber-800 dark:text-amber-200 border-amber-600/30 text-xs font-bold px-3 py-1">
                  <Bot className="h-3.5 w-3.5 mr-1 text-amber-600" />
                  Grounded Sartorial Intelligence
                </Badge>
                <Badge variant="outline" className="border-border text-muted-foreground text-xs font-semibold">
                  Zero Hallucinations (Strict Wardrobe Match)
                </Badge>
              </div>
              <h1 className="text-2xl sm:text-4xl font-serif font-black tracking-tight text-foreground">
                Verdict Stylist & Wardrobe Synthesizer
              </h1>
              <p className="text-xs sm:text-sm text-muted-foreground max-w-2xl">
                Chat with an AI stylist grounded exclusively in your indexed ChromaDB wardrobe embeddings. Get occasion outfits, layering strategies, and pairing recommendations with 0 phantom clothing recommendations.
              </p>
            </div>

            <div className="flex items-center gap-2 shrink-0">
              <Link href="/wardrobe">
                <Button variant="outline" size="sm" className="h-10 px-4 rounded-xl text-xs font-bold gap-2 border-border hover:bg-muted/40">
                  <Compass className="h-4 w-4 text-amber-600" />
                  <span>View All {wardrobeItems.length || "28"} Items</span>
                </Button>
              </Link>
            </div>
          </div>
        </div>

        {/* 2-COLUMN WIDESCREEN STUDIO GRID: 4 COLS CLOSET DRAWER | 8 COLS FULL CHAT */}
        <div className="grid grid-cols-1 lg:grid-cols-12 gap-6 items-start flex-1 min-h-[600px]">
          {/* LEFT COLUMN: WARDROBE QUICK STYLER & PALETTES (4 cols) — WARM BROWN & WHITE */}
          <div className="lg:col-span-4 space-y-6">
            {/* Quick Styler Drawer */}
            <Card className="border border-border/80 bg-card rounded-3xl shadow-sm overflow-hidden hover:border-amber-600/30 transition-colors">
              <CardHeader className="pb-3 border-b border-border/60 bg-muted/10">
                <div className="flex items-center justify-between">
                  <CardTitle className="text-base font-serif font-bold text-foreground flex items-center gap-2">
                    <FolderHeart className="h-4 w-4 text-amber-600" />
                    <span>My Wardrobe Items</span>
                  </CardTitle>
                  <span className="text-[11px] font-mono font-bold text-amber-800 dark:text-amber-300">
                    {wardrobeItems.length} Pieces
                  </span>
                </div>
                <CardDescription className="text-xs text-muted-foreground">
                  Click any piece below to immediately ask the Stylist how to style it:
                </CardDescription>
              </CardHeader>
              <CardContent className="p-4 space-y-3">
                {loadingWardrobe ? (
                  <div className="py-8 flex flex-col items-center justify-center gap-2">
                    <Loader2 className="h-5 w-5 animate-spin text-amber-600" />
                    <span className="text-xs text-muted-foreground">Loading wardrobe pieces...</span>
                  </div>
                ) : (
                  <div className="grid grid-cols-2 sm:grid-cols-3 gap-2.5 max-h-[360px] overflow-y-auto pr-1">
                    {wardrobeItems.slice(0, 15).map((item) => {
                      const catName = item.attributes?.category || "Item";
                      const colName = item.attributes?.color ? `${item.attributes.color} ` : "";
                      return (
                        <div
                          key={item.id}
                          onClick={() => handleStyleWardrobeItem(item)}
                          className="group relative p-2 rounded-2xl border border-border/80 bg-card hover:border-amber-600/50 hover:bg-amber-600/5 transition-all cursor-pointer flex flex-col items-center text-center space-y-1.5 shadow-2xs hover:scale-[1.02]"
                        >
                          <img
                            src={item.cloudinary_url}
                            alt={catName}
                            className="h-16 w-full object-cover rounded-xl border border-border"
                          />
                          <div className="w-full min-w-0">
                            <p className="text-[11px] font-bold text-foreground truncate">
                              {colName}{catName}
                            </p>
                            <p className="text-[9px] text-muted-foreground font-mono">
                              #{item.id}
                            </p>
                          </div>
                          <span className="text-[9px] text-amber-700 dark:text-amber-300 font-bold opacity-0 group-hover:opacity-100 transition-opacity">
                            Style this →
                          </span>
                        </div>
                      );
                    })}
                  </div>
                )}
              </CardContent>
            </Card>

            {/* Closet Color Harmony Card in Warm Brown & White */}
            <Card className="border border-border/80 bg-card rounded-3xl p-5 shadow-sm space-y-3 hover:border-amber-600/30 transition-colors">
              <div className="flex items-center justify-between border-b border-border/60 pb-2.5">
                <div className="flex items-center gap-2 text-xs font-bold uppercase text-foreground">
                  <Palette className="h-4 w-4 text-amber-600" />
                  <span>Wardrobe Palette Spectrum</span>
                </div>
                <Badge className="bg-amber-600/15 text-amber-800 dark:text-amber-200 border-amber-600/30 text-[10px]">
                  ChromaDB
                </Badge>
              </div>
              <p className="text-xs text-muted-foreground leading-relaxed">
                Your wardrobe core is anchored in timeless luxury neutrals. Click any colorway to ask for outfits featuring that hue:
              </p>
              <div className="grid grid-cols-3 gap-2 pt-1">
                {[
                  { name: "Cognac Camel", hex: "#AD7E4A" },
                  { name: "Obsidian", hex: "#171717" },
                  { name: "Ivory White", hex: "#FAF7F2" },
                  { name: "Warm Amber", hex: "#C29B38" },
                  { name: "Charcoal", hex: "#334155" },
                  { name: "Espresso", hex: "#3E2723" },
                ].map((c) => (
                  <button
                    key={c.name}
                    onClick={() => handleSend(`Show me outfit pairings featuring ${c.name} from my wardrobe.`)}
                    className="flex items-center gap-2 p-2 rounded-xl border bg-card hover:bg-muted/40 transition-colors text-left cursor-pointer"
                  >
                    <div className="h-4 w-4 rounded-full border shadow-2xs shrink-0" style={{ backgroundColor: c.hex }} />
                    <span className="text-[10px] font-bold text-foreground truncate">{c.name}</span>
                  </button>
                ))}
              </div>
            </Card>

            {/* Grounding Telemetry Box */}
            <div className="p-4 rounded-3xl border border-amber-600/30 bg-amber-600/5 space-y-2 text-xs">
              <div className="flex items-center gap-2 font-bold text-amber-800 dark:text-amber-300">
                <ShieldCheck className="h-4 w-4 text-amber-600" />
                <span>Deterministic Grounding Active</span>
              </div>
              <p className="text-[11px] text-muted-foreground leading-relaxed">
                Every suggestion citations real item IDs from your SQLite & ChromaDB wardrobe graph. Out-of-distribution queries trigger guardrails with zero hallucination.
              </p>
            </div>
          </div>

          {/* RIGHT COLUMN: MAIN CHAT FEED & INPUT (8 cols) */}
          <div className="lg:col-span-8 space-y-4 flex flex-col flex-1">
            {/* Starter Suggestion Pills in Warm Brown & White Style */}
            <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
              <span className="text-xs font-bold text-muted-foreground shrink-0 flex items-center gap-1.5 uppercase tracking-wider">
                <Sparkles className="w-3.5 h-3.5 text-amber-600" /> Prompts:
              </span>
              {STARTER_PROMPTS.map((prompt, idx) => (
                <button
                  key={idx}
                  onClick={() => handleSend(prompt.title)}
                  disabled={isLoading}
                  className={`text-xs px-3.5 py-2 rounded-2xl border transition-all shrink-0 flex items-center gap-2 select-none shadow-2xs font-semibold cursor-pointer hover:scale-[1.02] ${
                    prompt.isGuardrailTest
                      ? "bg-amber-600/15 border-amber-600/40 text-amber-800 dark:text-amber-200"
                      : "bg-card border-border/80 hover:border-amber-600/40 text-foreground"
                  }`}
                >
                  <span>{prompt.title}</span>
                  {prompt.isGuardrailTest && (
                    <Badge variant="consider" className="text-[9px] uppercase font-bold tracking-wider px-1.5 py-0 rounded">
                      Guardrail
                    </Badge>
                  )}
                </button>
              ))}
            </div>

            {/* Message Feed Card */}
            <Card className="flex-1 bg-card/90 border border-border/80 shadow-md flex flex-col overflow-hidden rounded-3xl min-h-[560px]">
              <CardContent className="flex-1 overflow-y-auto p-4 sm:p-6 flex flex-col gap-5">
                <AnimatePresence initial={false}>
                  {messages.map((msg) => (
                    <motion.div
                      key={msg.id}
                      initial="hidden"
                      animate="visible"
                      variants={fadeUpVariants}
                      className={`flex gap-3.5 max-w-[90%] md:max-w-[82%] ${
                        msg.sender === "user" ? "self-end flex-row-reverse" : "self-start"
                      }`}
                    >
                      {/* Sender Avatar */}
                      <div
                        className={`w-9 h-9 rounded-2xl flex items-center justify-center shrink-0 text-xs font-bold shadow-sm ${
                          msg.sender === "user"
                            ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900"
                            : "bg-amber-600 text-white border border-amber-600/40"
                        }`}
                      >
                        {msg.sender === "user" ? <UserIcon className="w-4 h-4" /> : <Bot className="w-4 h-4" />}
                      </div>

                      {/* Message Bubble & Content */}
                      <div className="flex flex-col gap-2">
                        <div
                          className={`p-4 sm:p-5 rounded-3xl text-sm leading-relaxed ${
                            msg.sender === "user"
                              ? "bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 rounded-tr-xs shadow-md"
                              : "bg-muted/30 border border-border/80 text-foreground rounded-tl-xs shadow-xs"
                          }`}
                        >
                          <p className="whitespace-pre-wrap">{msg.text}</p>
                        </div>

                        {/* Structural Guardrail Banner */}
                        {msg.guardrail_triggered && (
                          <motion.div
                            initial={{ opacity: 0, scale: 0.95 }}
                            animate={{ opacity: 1, scale: 1 }}
                            className="bg-amber-500/10 border border-amber-500/30 rounded-2xl p-3.5 text-xs text-amber-800 dark:text-amber-300 flex items-start gap-2.5 shadow-xs"
                          >
                            <ShieldAlert className="w-4 h-4 text-amber-600 shrink-0 mt-0.5" />
                            <div>
                              <p className="font-bold flex items-center gap-1.5">
                                Structural Guardrail Activated
                                <span className="text-[10px] font-normal px-1.5 py-0.5 rounded bg-amber-500/20 border border-amber-500/30">
                                  0 LLM Tokens
                                </span>
                              </p>
                              <p className="text-[11px] text-muted-foreground mt-0.5">
                                Query was ungrounded in your wardrobe. Redirected deterministically without hallucination.
                              </p>
                            </div>
                          </motion.div>
                        )}

                        {/* Traceable Grounding Items Shelf */}
                        {msg.retrieved_items && msg.retrieved_items.length > 0 && (
                          <div className="bg-muted/20 border border-border/80 rounded-2xl p-3.5 flex flex-col gap-2.5">
                            <div className="flex items-center justify-between text-xs font-semibold">
                              <span className="flex items-center gap-1.5 text-foreground">
                                <Sparkles className="w-3.5 h-3.5 text-amber-600" />
                                Grounded in {msg.retrieved_items.length} wardrobe {msg.retrieved_items.length === 1 ? "item" : "items"}:
                              </span>
                              {msg.provider_used && (
                                <span className="text-[10px] text-muted-foreground font-mono">
                                  via {msg.provider_used}
                                </span>
                              )}
                            </div>

                            {/* Chips container */}
                            <div className="grid grid-cols-1 sm:grid-cols-2 gap-2.5 pt-1">
                              {msg.retrieved_items.map((item) => (
                                <div
                                  key={item.id}
                                  className="flex items-center gap-3 bg-card border border-border hover:border-amber-600/40 rounded-xl p-2.5 transition shadow-2xs group"
                                >
                                  {item.thumbnail_url ? (
                                    <img
                                      src={item.thumbnail_url}
                                      alt={item.category}
                                      className="w-12 h-12 rounded-xl object-cover bg-muted shrink-0 border"
                                    />
                                  ) : (
                                    <div className="w-12 h-12 rounded-xl bg-muted/80 flex items-center justify-center text-muted-foreground shrink-0 border">
                                      <Shirt className="w-6 h-6" />
                                    </div>
                                  )}
                                  <div className="min-w-0 flex-1">
                                    <div className="flex items-center justify-between gap-1">
                                      <p className="text-xs font-bold text-foreground truncate capitalize">
                                        {item.color} {item.category}
                                      </p>
                                      <Badge variant="buy" className="text-[10px] font-bold px-2 py-0.5 rounded-md shrink-0">
                                        {Math.round(item.similarity_score)}%
                                      </Badge>
                                    </div>
                                    <p className="text-[10px] text-muted-foreground truncate mt-0.5 font-mono">
                                      #{item.id} • {item.style} • {item.season}
                                    </p>
                                  </div>
                                </div>
                              ))}
                            </div>
                          </div>
                        )}

                        <span className="text-[10px] text-muted-foreground px-1 self-end font-mono">
                          {msg.timestamp}
                        </span>
                      </div>
                    </motion.div>
                  ))}
                </AnimatePresence>

                {/* Loading Indicator */}
                {isLoading && (
                  <motion.div
                    initial={{ opacity: 0, y: 10 }}
                    animate={{ opacity: 1, y: 0 }}
                    className="flex gap-3.5 self-start items-center max-w-[80%]"
                  >
                    <div className="w-9 h-9 rounded-2xl bg-amber-600 text-white flex items-center justify-center shrink-0 border border-amber-600/40">
                      <Bot className="w-4 h-4" />
                    </div>
                    <div className="p-4 rounded-2xl bg-card border text-muted-foreground text-xs flex items-center gap-2.5 shadow-xs">
                      <Loader2 className="w-4 h-4 animate-spin text-amber-600" />
                      <span>Synthesizing wardrobe pairings & grounded styling advice...</span>
                    </div>
                  </motion.div>
                )}

                <div ref={messagesEndRef} />
              </CardContent>

              {/* Error Banner */}
              {error && (
                <div className="mx-4 mb-2 p-3 rounded-2xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
                  <Info className="w-4 h-4 shrink-0" />
                  <span>{error}</span>
                </div>
              )}

              {/* Input Bar */}
              <div className="p-4 bg-card/95 border-t border-border/80 flex items-center gap-3">
                <Input
                  value={input}
                  onChange={(e) => setInput(e.target.value)}
                  onKeyDown={handleKeyDown}
                  disabled={isLoading}
                  placeholder="Ask about outfit pairings, styling an item, or occasion rules..."
                  className="bg-background border-border focus-visible:ring-amber-600 text-sm text-foreground placeholder:text-muted-foreground h-12 rounded-2xl px-4"
                />
                <Button
                  onClick={() => handleSend()}
                  disabled={isLoading || !input.trim()}
                  className="h-12 px-5 rounded-2xl font-bold bg-neutral-900 text-white hover:bg-black dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-100 shrink-0 disabled:opacity-50 transition shadow-sm cursor-pointer"
                >
                  {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
                </Button>
              </div>
            </Card>
          </div>
        </div>
      </main>
    </div>
  );
}
