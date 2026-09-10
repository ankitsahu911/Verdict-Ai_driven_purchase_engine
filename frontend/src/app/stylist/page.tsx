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
} from "lucide-react";
import { Card, CardContent, CardHeader, CardTitle } from "@/components/ui/card";
import { Button } from "@/components/ui/button";
import { Badge } from "@/components/ui/badge";
import { Input } from "@/components/ui/input";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { NavigationHeader } from "@/components/NavigationHeader";
import { fadeUpVariants } from "@/lib/animations";
import {
  chatWithStylist,
  type RetrievedWardrobeItemData,
  type StylistChatResponseData,
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
    title: "What goes with my blue jacket?",
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
  const messagesEndRef = useRef<HTMLDivElement>(null);

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: "smooth" });
  };

  useEffect(() => {
    scrollToBottom();
  }, [messages, isLoading]);

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
      const response: StylistChatResponseData = await chatWithStylist(query, 5);

      const assistantMessage: ChatMessage = {
        id: `assistant-${Date.now()}`,
        sender: "assistant",
        text: response.reply,
        retrieved_items: response.retrieved_items || [],
        provider_used: response.provider_used,
        model_used: response.model_used,
        guardrail_triggered: response.guardrail_triggered,
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

  return (
    <div className="min-h-screen bg-background text-foreground flex flex-col">
      <NavigationHeader currentSubtitle="Stylist Chat" badgeText="Grounded RAG" />

      {/* Main Chat Container */}
      <main className="flex-1 max-w-4xl w-full mx-auto p-4 md:p-6 flex flex-col gap-4">
        {/* Starter Suggestion Pills */}
        <div className="flex items-center gap-2 overflow-x-auto pb-1 scrollbar-none">
          <span className="text-xs font-medium text-muted-foreground shrink-0 flex items-center gap-1">
            <Sparkles className="w-3 h-3 text-primary" /> Prompts:
          </span>
          {STARTER_PROMPTS.map((prompt, idx) => (
            <button
              key={idx}
              onClick={() => handleSend(prompt.title)}
              disabled={isLoading}
              className={`text-xs px-3 py-1.5 rounded-full border transition shrink-0 flex items-center gap-1.5 select-none ${
                prompt.isGuardrailTest
                  ? "bg-amber-500/10 border-amber-500/30 text-amber-700 dark:text-amber-300 hover:bg-amber-500/20"
                  : "bg-card border-border text-muted-foreground hover:bg-muted/70 hover:text-foreground"
              }`}
            >
              <span>{prompt.title}</span>
              {prompt.isGuardrailTest && (
                <Badge variant="consider" className="text-[9px] uppercase font-bold tracking-wider px-1 py-0 rounded">
                  Guardrail Test
                </Badge>
              )}
            </button>
          ))}
        </div>

        {/* Message Feed */}
        <Card className="flex-1 bg-card/80 border shadow-md flex flex-col overflow-hidden rounded-2xl min-h-[520px]">
          <CardContent className="flex-1 overflow-y-auto p-4 md:p-6 flex flex-col gap-5">
            <AnimatePresence initial={false}>
              {messages.map((msg) => (
                <motion.div
                  key={msg.id}
                  initial="hidden"
                  animate="visible"
                  variants={fadeUpVariants}
                  className={`flex gap-3 max-w-[85%] md:max-w-[78%] ${
                    msg.sender === "user" ? "self-end flex-row-reverse" : "self-start"
                  }`}
                >
                  {/* Sender Avatar */}
                  <div
                    className={`w-8 h-8 rounded-full flex items-center justify-center shrink-0 text-xs font-medium ${
                      msg.sender === "user"
                        ? "bg-indigo-600 text-white shadow-md shadow-indigo-600/30"
                        : "bg-zinc-800 text-zinc-300 border border-zinc-700"
                    }`}
                  >
                    {msg.sender === "user" ? <UserIcon className="w-4 h-4" /> : <Bot className="w-4 h-4 text-indigo-400" />}
                  </div>

                  {/* Message Bubble & Content */}
                  <div className="flex flex-col gap-2">
                    <div
                      className={`p-4 rounded-2xl text-sm leading-relaxed ${
                        msg.sender === "user"
                          ? "bg-indigo-600 text-white rounded-tr-xs shadow-md shadow-indigo-600/10"
                          : "bg-zinc-900/90 border border-zinc-800/80 text-zinc-100 rounded-tl-xs shadow-sm"
                      }`}
                    >
                      <p className="whitespace-pre-wrap">{msg.text}</p>
                    </div>

                    {/* Structural Guardrail Banner */}
                    {msg.guardrail_triggered && (
                      <motion.div
                        initial={{ opacity: 0, scale: 0.95 }}
                        animate={{ opacity: 1, scale: 1 }}
                        className="bg-amber-950/40 border border-amber-800/50 rounded-xl p-3 text-xs text-amber-200 flex items-start gap-2.5 shadow-sm"
                      >
                        <ShieldAlert className="w-4 h-4 text-amber-400 shrink-0 mt-0.5" />
                        <div>
                          <p className="font-semibold text-amber-300 flex items-center gap-1.5">
                            Structural Guardrail Activated
                            <span className="text-[10px] font-normal px-1.5 py-0.5 rounded bg-amber-500/20 text-amber-300 border border-amber-500/30">
                              0 LLM Tokens
                            </span>
                          </p>
                          <p className="text-zinc-400 text-[11px] mt-0.5">
                            Query was ungrounded in your wardrobe (no items met semantic similarity threshold). Redirected deterministically without hallucination.
                          </p>
                        </div>
                      </motion.div>
                    )}

                    {/* Traceable Grounding Items Shelf */}
                    {msg.retrieved_items && msg.retrieved_items.length > 0 && (
                      <div className="bg-zinc-950/60 border border-zinc-800/70 rounded-xl p-3 flex flex-col gap-2">
                        <div className="flex items-center justify-between text-xs text-zinc-400 font-medium">
                          <span className="flex items-center gap-1.5 text-zinc-300">
                            <Sparkles className="w-3.5 h-3.5 text-indigo-400" />
                            Grounded in {msg.retrieved_items.length} wardrobe {msg.retrieved_items.length === 1 ? "item" : "items"}:
                          </span>
                          {msg.provider_used && (
                            <span className="text-[10px] text-zinc-500 font-mono">
                              via {msg.provider_used}
                            </span>
                          )}
                        </div>

                        {/* Chips container */}
                        <div className="grid grid-cols-1 sm:grid-cols-2 gap-2 pt-1">
                          {msg.retrieved_items.map((item) => (
                            <div
                              key={item.id}
                              className="flex items-center gap-2.5 bg-card/90 border border-border hover:border-muted-foreground/40 rounded-xl p-2.5 transition shadow-xs group"
                            >
                              {item.thumbnail_url ? (
                                <img
                                  src={item.thumbnail_url}
                                  alt={item.category}
                                  className="w-10 h-10 rounded-lg object-cover bg-muted shrink-0 border"
                                />
                              ) : (
                                <div className="w-10 h-10 rounded-lg bg-muted/80 flex items-center justify-center text-muted-foreground shrink-0 border">
                                  <Shirt className="w-5 h-5" />
                                </div>
                              )}
                              <div className="min-w-0 flex-1">
                                <div className="flex items-center justify-between gap-1">
                                  <p className="text-xs font-bold text-foreground truncate capitalize">
                                    {item.color} {item.category}
                                  </p>
                                  <Badge variant="buy" className="text-[10px] font-bold px-1.5 py-0.5 rounded-md shrink-0">
                                    {Math.round(item.similarity_score)}%
                                  </Badge>
                                </div>
                                <p className="text-[10px] text-muted-foreground truncate mt-0.5">
                                  #{item.id} • {item.style} • {item.season}
                                </p>
                              </div>
                            </div>
                          ))}
                        </div>
                      </div>
                    )}

                    <span className="text-[10px] text-muted-foreground px-1 self-end">
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
                className="flex gap-3 self-start items-center max-w-[80%]"
              >
                <div className="w-8 h-8 rounded-full bg-muted flex items-center justify-center shrink-0 border">
                  <Bot className="w-4 h-4 text-primary" />
                </div>
                <div className="p-3.5 rounded-2xl bg-card border text-muted-foreground text-xs flex items-center gap-2.5 shadow-xs">
                  <Loader2 className="w-3.5 h-3.5 animate-spin text-primary" />
                  <span>Searching wardrobe embeddings & synthesizing advice...</span>
                </div>
              </motion.div>
            )}

            <div ref={messagesEndRef} />
          </CardContent>

          {/* Error Banner */}
          {error && (
            <div className="mx-4 mb-2 p-2.5 rounded-xl bg-destructive/10 border border-destructive/20 text-destructive text-xs flex items-center gap-2">
              <Info className="w-4 h-4 shrink-0" />
              <span>{error}</span>
            </div>
          )}

          {/* Input Bar */}
          <div className="p-3.5 bg-card/90 border-t flex items-center gap-2">
            <Input
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              disabled={isLoading}
              placeholder="Ask about outfit pairings, occasions, or items in your closet..."
              className="bg-background border-border focus-visible:ring-primary text-sm text-foreground placeholder:text-muted-foreground h-11 rounded-xl"
            />
            <Button
              onClick={() => handleSend()}
              disabled={isLoading || !input.trim()}
              className="h-11 px-4 rounded-xl font-medium shrink-0 disabled:opacity-50 transition shadow-sm"
            >
              {isLoading ? <Loader2 className="w-4 h-4 animate-spin" /> : <Send className="w-4 h-4" />}
            </Button>
          </div>
        </Card>
      </main>
    </div>
  );
}
