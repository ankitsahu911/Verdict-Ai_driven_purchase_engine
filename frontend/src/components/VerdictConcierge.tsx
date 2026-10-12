"use client";

import React, { useState, useRef, useEffect } from "react";
import { motion, AnimatePresence } from "framer-motion";
import {
  Sparkles,
  X,
  Send,
  Loader2,
  Bot,
  User as UserIcon,
  RotateCcw,
  CheckCircle2,
  AlertTriangle,
  ChevronRight,
  ExternalLink,
  Shirt,
  MessageSquare,
} from "lucide-react";
import { Badge } from "@/components/ui/badge";
import { Button } from "@/components/ui/button";
import { chatWithStylist, type RetrievedWardrobeItemData } from "@/lib/api";

interface ChatMessage {
  id: string;
  sender: "user" | "assistant";
  text: string;
  retrievedItems?: RetrievedWardrobeItemData[];
  timestamp: string;
  statusBadge?: string;
}

const CONCIERGE_SUGGESTIONS = [
  {
    label: "Why is Candidate #32 a SKIP?",
    query: "Why did Candidate #32 get a SKIP verdict? Explain the duplicate overlap and reason.",
  },
  {
    label: "Explain Top Strategy Buy A + C",
    query: "Explain why Buy A + C is the top What-If combination and what value it creates.",
  },
  {
    label: "How does Candidate #33 pair?",
    query: "How does Candidate #33 pair with my current wardrobe pieces?",
  },
  {
    label: "What is my biggest wardrobe gap?",
    query: "Based on my 24 wardrobe items, what categories or seasonal pieces am I missing?",
  },
];

export function VerdictConcierge() {
  const [isOpen, setIsOpen] = useState(false);
  const [messages, setMessages] = useState<ChatMessage[]>([
    {
      id: "initial-greeting",
      sender: "assistant",
      text: "Bonjour. I am your Verdict Concierge — an AI purchase decision advisor. I evaluate cart additions against your 24 wardrobe pieces, explain 6-axis Buy Scores, and optimize your cart combinations. How may I assist your decision today?",
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    },
  ]);
  const [inputText, setInputText] = useState("");
  const [isLoading, setIsLoading] = useState(false);
  const messagesEndRef = useRef<HTMLDivElement | null>(null);
  const inputRef = useRef<HTMLInputElement | null>(null);

  useEffect(() => {
    if (isOpen) {
      setTimeout(() => {
        messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
        inputRef.current?.focus();
      }, 150);
    }
  }, [isOpen, messages]);

  const handleSendMessage = async (textToSend?: string) => {
    const query = (textToSend || inputText).trim();
    if (!query || isLoading) return;

    const userMessage: ChatMessage = {
      id: `user-${Date.now()}`,
      sender: "user",
      text: query,
      timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
    };

    setMessages((prev) => [...prev, userMessage]);
    setInputText("");
    setIsLoading(true);

    try {
      // Call backend grounded stylist / decision RAG endpoint
      const response = await chatWithStylist(query, 4);

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: "assistant",
        text: response.reply,
        retrievedItems: response.retrieved_items,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        statusBadge: response.guardrail_triggered ? "Safety Filtered" : "Closet Verified",
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } catch (err: any) {
      // Smart Fallback grounded in Verdict's deterministic demo data
      let fallbackReply = "";
      const lower = query.toLowerCase();

      if (lower.includes("32") || lower.includes("skip")) {
        fallbackReply =
          "**Candidate #32 Verdict: SKIP (Score: 41.0 / 100)**\n\n" +
          "• **Duplicate Risk (96.0%)**: Almost identical in cut, fabric, and colorway to an existing charcoal jacket in your closet (ID #14).\n" +
          "• **Versatility Impact**: Only yields +1 marginal new outfit pairing.\n" +
          "• **Recommendation**: Skip this purchase to prevent redundant closet accumulation and redirect budget toward unfilled seasonal gaps.";
      } else if (lower.includes("33") || lower.includes("buy") || lower.includes("pair")) {
        fallbackReply =
          "**Candidate #33 Verdict: BUY (Score: 81.2 / 100)**\n\n" +
          "• **High Uniqueness**: Only 12.0% closet duplicate risk — introduces a fresh silhouette.\n" +
          "• **Versatility Multiplier**: Immediately unlocks +5 complete outfits across your existing neutral trousers and knitwear.\n" +
          "• **Cost-per-Wear**: Projected at $2.80/wear over 12 months with high autumn/winter utility.";
      } else if (lower.includes("what-if") || lower.includes("strategy") || lower.includes("a + c") || lower.includes("bundle")) {
        fallbackReply =
          "**What-If Lab Top Strategy: Buy A + C (Score: 81.8 / 100)**\n\n" +
          "• **Combinatorial Synergy**: Purchasing Candidates A & C together unlocks 23 coordinated outfits while preserving 82% of your seasonal budget.\n" +
          "• **Sub-optimal Alternatives**: Buying all 4 candidates (A+B+C+D) causes severe duplicate overlap (38% redundant) and drops total score to 56.4.";
      } else {
        fallbackReply =
          "Based on your 24 indexed wardrobe items:\n\n" +
          "• **Current Closet State**: Strong foundation in core neutrals (65% outerwear & bottoms), with high versatility scores.\n" +
          "• **Active Cart Audit**: 1 clear recommended purchase (Candidate #33) and 1 identified duplicate risk to avoid (Candidate #32).\n" +
          "• You can test alternative cart combinations in the **What-If Lab** or examine the 6-axis breakdown in the **Verdict Visualizer**.";
      }

      const assistantMessage: ChatMessage = {
        id: `assistant-fallback-${Date.now()}`,
        sender: "assistant",
        text: fallbackReply,
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
        statusBadge: "Grounded Heuristic",
      };

      setMessages((prev) => [...prev, assistantMessage]);
    } finally {
      setIsLoading(false);
    }
  };

  const clearChat = () => {
    setMessages([
      {
        id: "cleared-greeting",
        sender: "assistant",
        text: "Chat cleared. Ask me anything regarding your candidate garments, outfit synergies, or What-If purchase decisions.",
        timestamp: new Date().toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" }),
      },
    ]);
  };

  return (
    <>
      {/* Floating Concierge Launcher Button */}
      <div className="fixed bottom-6 right-6 z-50">
        <motion.button
          onClick={() => setIsOpen(!isOpen)}
          whileHover={{ scale: 1.05, y: -2 }}
          whileTap={{ scale: 0.95 }}
          className="relative group flex items-center gap-3 p-1.5 pr-4 rounded-full bg-card/90 dark:bg-[#1b1424]/90 backdrop-blur-xl border border-border/80 dark:border-[#342646] shadow-2xl shadow-primary/20 hover:border-primary/50 transition-all cursor-pointer"
          aria-label="Toggle Verdict Decision Concierge"
        >
          {/* Glowing Animated Ring */}
          <div className="relative flex h-10 w-10 items-center justify-center rounded-full brand-gradient-bg text-white font-bold shadow-md">
            {isOpen ? (
              <X className="h-5 w-5 transition-transform group-hover:rotate-90 duration-200" />
            ) : (
              <Sparkles className="h-5 w-5 animate-pulse" />
            )}
            <span className="absolute top-0 right-0 h-3 w-3 rounded-full bg-amber-500 ring-2 ring-background animate-ping" />
            <span className="absolute top-0 right-0 h-3 w-3 rounded-full bg-amber-500 ring-2 ring-background" />
          </div>

          <div className="text-left select-none">
            <div className="flex items-center gap-1.5">
              <span className="text-xs font-bold tracking-tight text-foreground">
                Verdict Concierge
              </span>
              <span className="text-[10px] px-1.5 py-0.2 rounded-full bg-primary/10 text-primary font-semibold">
                AI
              </span>
            </div>
            <p className="text-[10px] text-muted-foreground font-medium -mt-0.5">
              Decision & Styling Advisor
            </p>
          </div>
        </motion.button>
      </div>

      {/* Floating Chat Modal Panel */}
      <AnimatePresence>
        {isOpen && (
          <motion.div
            initial={{ opacity: 0, y: 30, scale: 0.94 }}
            animate={{ opacity: 1, y: 0, scale: 1 }}
            exit={{ opacity: 0, y: 20, scale: 0.94 }}
            transition={{ type: "spring", stiffness: 350, damping: 28 }}
            className="fixed bottom-24 right-4 sm:right-6 z-50 w-[400px] sm:w-[430px] max-w-[calc(100vw-2rem)] h-[600px] max-h-[82vh] rounded-3xl bg-card/95 dark:bg-[#1b1424]/95 backdrop-blur-2xl border border-border/80 dark:border-[#342646] shadow-2xl flex flex-col overflow-hidden"
          >
            {/* Concierge Header */}
            <div className="p-4 border-b border-border/60 dark:border-[#342646]/80 flex items-center justify-between bg-secondary/30 dark:bg-[#171020]/50 shrink-0">
              <div className="flex items-center gap-2.5">
                <div className="h-9 w-9 rounded-2xl brand-gradient-bg flex items-center justify-center text-white font-black text-sm shadow-sm">
                  V
                </div>
                <div>
                  <div className="flex items-center gap-1.5">
                    <h3 className="font-extrabold text-sm text-foreground tracking-tight">
                      Verdict Concierge
                    </h3>
                    <Badge
                      variant="outline"
                      className="text-[9px] px-1.5 py-0 bg-primary/10 text-primary border-primary/20"
                    >
                      Grounded RAG
                    </Badge>
                  </div>
                  <p className="text-[11px] text-muted-foreground flex items-center gap-1">
                    <span className="h-1.5 w-1.5 rounded-full bg-amber-500 inline-block" />
                    24 wardrobe items indexed
                  </p>
                </div>
              </div>

              <div className="flex items-center gap-1">
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={clearChat}
                  title="Clear conversation"
                  className="h-8 w-8 text-muted-foreground hover:text-foreground rounded-full"
                >
                  <RotateCcw className="h-3.5 w-3.5" />
                </Button>
                <Button
                  variant="ghost"
                  size="icon"
                  onClick={() => setIsOpen(false)}
                  className="h-8 w-8 text-muted-foreground hover:text-foreground rounded-full"
                >
                  <X className="h-4 w-4" />
                </Button>
              </div>
            </div>

            {/* Messages Body */}
            <div className="flex-1 overflow-y-auto p-4 space-y-3.5 scrollbar-thin scrollbar-thumb-muted-foreground/20">
              {messages.map((msg) => {
                const isUser = msg.sender === "user";
                return (
                  <div
                    key={msg.id}
                    className={`flex flex-col ${isUser ? "items-end" : "items-start"}`}
                  >
                    <div
                      className={`max-w-[88%] rounded-2xl px-3.5 py-2.5 text-xs leading-relaxed ${
                        isUser
                          ? "brand-gradient-bg text-white shadow-sm rounded-br-xs font-medium"
                          : "bg-secondary/70 dark:bg-[#241a30]/80 text-foreground border border-border/50 dark:border-[#342646] rounded-bl-xs shadow-2xs"
                      }`}
                    >
                      {/* Render text with simple markdown bullets support */}
                      <div className="whitespace-pre-line space-y-1">
                        {msg.text.split("\n").map((line, idx) => {
                          if (line.startsWith("• ") || line.startsWith("* ")) {
                            return (
                              <div key={idx} className="flex items-start gap-1.5 pl-1 my-0.5">
                                <span className="text-primary font-bold shrink-0">•</span>
                                <span>{line.replace(/^[•*]\s*/, "")}</span>
                              </div>
                            );
                          }
                          if (line.startsWith("**") && line.endsWith("**")) {
                            return (
                              <p key={idx} className="font-bold text-foreground text-xs my-0.5">
                                {line.replace(/\*\*/g, "")}
                              </p>
                            );
                          }
                          return line ? <p key={idx}>{line}</p> : <div key={idx} className="h-1" />;
                        })}
                      </div>

                      {/* Wardrobe Items retrieved pills (if any) */}
                      {msg.retrievedItems && msg.retrievedItems.length > 0 && (
                        <div className="mt-2.5 pt-2 border-t border-border/30 dark:border-white/10 space-y-1.5">
                          <p className="text-[10px] font-semibold text-muted-foreground uppercase tracking-wider">
                            Closet Context Referenced:
                          </p>
                          <div className="flex flex-wrap gap-1.5">
                            {msg.retrievedItems.slice(0, 3).map((item) => (
                              <span
                                key={item.id}
                                className="inline-flex items-center gap-1 text-[10px] px-2 py-0.5 rounded-full bg-background/60 dark:bg-black/30 border border-border/40 text-foreground/90 font-medium"
                              >
                                <Shirt className="h-2.5 w-2.5 text-primary" />
                                {item.color} {item.category} ({Math.round(item.similarity_score * 100)}% match)
                              </span>
                            ))}
                          </div>
                        </div>
                      )}
                    </div>

                    <div className="flex items-center gap-2 mt-1 px-1">
                      <span className="text-[9px] text-muted-foreground font-mono">
                        {msg.timestamp}
                      </span>
                      {msg.statusBadge && (
                        <span className="text-[9px] font-semibold text-primary/80">
                          {msg.statusBadge}
                        </span>
                      )}
                    </div>
                  </div>
                );
              })}

              {isLoading && (
                <div className="flex items-center gap-2 text-xs text-muted-foreground p-2 rounded-xl bg-secondary/40 dark:bg-[#241a30]/40 w-fit animate-pulse">
                  <Loader2 className="h-3.5 w-3.5 animate-spin text-primary" />
                  <span>Evaluating decision graph...</span>
                </div>
              )}

              <div ref={messagesEndRef} />
            </div>

            {/* Quick Suggestions Chips */}
            <div className="px-3 py-2 bg-secondary/20 dark:bg-[#171020]/30 border-t border-border/40 shrink-0">
              <div className="text-[10px] text-muted-foreground font-medium mb-1 px-1 flex items-center justify-between">
                <span>Suggested Queries:</span>
                <span className="text-[9px] text-primary">Tap to ask</span>
              </div>
              <div className="flex gap-1.5 overflow-x-auto pb-1 scrollbar-none">
                {CONCIERGE_SUGGESTIONS.map((sugg, i) => (
                  <button
                    key={i}
                    onClick={() => handleSendMessage(sugg.query)}
                    className="text-[10.5px] whitespace-nowrap px-2.5 py-1 rounded-full bg-card dark:bg-[#241a30] border border-border/60 hover:border-primary/50 text-foreground/80 hover:text-primary transition-colors shrink-0 shadow-2xs font-medium cursor-pointer"
                  >
                    {sugg.label}
                  </button>
                ))}
              </div>
            </div>

            {/* Input Footer */}
            <div className="p-3 border-t border-border/60 dark:border-[#342646]/80 bg-card/80 dark:bg-[#1b1424]/90 shrink-0">
              <form
                onSubmit={(e) => {
                  e.preventDefault();
                  handleSendMessage();
                }}
                className="flex items-center gap-2"
              >
                <input
                  ref={inputRef}
                  type="text"
                  value={inputText}
                  onChange={(e) => setInputText(e.target.value)}
                  placeholder="Ask about cart items, outfits, scores..."
                  disabled={isLoading}
                  className="flex-1 bg-secondary/50 dark:bg-[#241a30]/60 border border-border/60 dark:border-[#342646] rounded-2xl px-3.5 py-2 text-xs text-foreground placeholder:text-muted-foreground focus:outline-none focus:ring-1.5 focus:ring-primary/40 transition-all"
                />
                <Button
                  type="submit"
                  size="icon"
                  disabled={!inputText.trim() || isLoading}
                  className="h-8 w-8 rounded-xl brand-gradient-bg text-white hover:opacity-90 transition-opacity shrink-0 shadow-sm"
                >
                  {isLoading ? (
                    <Loader2 className="h-3.5 w-3.5 animate-spin" />
                  ) : (
                    <Send className="h-3.5 w-3.5" />
                  )}
                </Button>
              </form>
            </div>
          </motion.div>
        )}
      </AnimatePresence>
    </>
  );
}
