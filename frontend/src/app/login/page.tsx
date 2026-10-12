"use client";

import { useState, type FormEvent } from "react";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { useAuth } from "@/contexts/AuthContext";
import { Sparkles, KeyRound, UserCheck, ArrowRight, ShieldCheck, Lock, Mail } from "lucide-react";
import { Button } from "@/components/ui/button";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const [loading, setLoading] = useState(false);
  const router = useRouter();
  const { loginWithEmail, loginAsDemo } = useAuth();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!email || !password) {
      setError("Please provide both email and password.");
      return;
    }
    setLoading(true);
    try {
      const ok = await loginWithEmail(email, password);
      if (ok) {
        router.push("/");
      } else {
        setError("Invalid email or password.");
      }
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Authentication error");
    } finally {
      setLoading(false);
    }
  }

  function handleAutoFillUser() {
    setEmail("anknk@verdict.ai");
    setPassword("verdict2026");
  }

  async function handleQuickLoginUser() {
    setLoading(true);
    await loginWithEmail("anknk@verdict.ai", "verdict2026");
    router.push("/");
  }

  function handleDemoLogin() {
    loginAsDemo();
    router.push("/");
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-4 sm:p-6 bg-background text-foreground transition-colors duration-200">
      <div className="w-full max-w-md rounded-3xl border border-border/80 bg-card p-8 sm:p-10 shadow-xl space-y-7">
        {/* Brand Header */}
        <div className="text-center space-y-2">
          <div className="inline-flex h-12 w-12 items-center justify-center rounded-2xl bg-neutral-900 text-white dark:bg-white dark:text-neutral-900 font-serif font-black text-2xl shadow-md mb-1">
            V
          </div>
          <h1 className="text-2xl sm:text-3xl font-serif font-bold tracking-tight text-foreground">
            Sign In to Verdict
          </h1>
          <p className="text-xs sm:text-sm text-muted-foreground font-medium">
            AI-Driven Purchase Engine & Luxury Wardrobe Architect
          </p>
        </div>

        {/* Pre-Created Personal Account Card */}
        <div className="p-4 rounded-2xl border border-amber-600/30 bg-amber-500/10 space-y-3">
          <div className="flex items-center justify-between">
            <div className="flex items-center gap-2 text-amber-800 dark:text-amber-200 font-bold text-xs">
              <Sparkles className="h-4 w-4 text-amber-600 dark:text-amber-400 shrink-0" />
              <span>Your Pre-Configured Account</span>
            </div>
            <span className="text-[10px] font-mono font-bold px-2 py-0.5 rounded-md bg-amber-600/20 text-amber-800 dark:text-amber-200">
              Active
            </span>
          </div>

          <div className="text-xs space-y-1 bg-card/80 p-2.5 rounded-xl border border-border/60">
            <div className="flex justify-between items-center text-muted-foreground">
              <span>Email:</span>
              <span className="font-mono font-bold text-foreground">anknk@verdict.ai</span>
            </div>
            <div className="flex justify-between items-center text-muted-foreground">
              <span>Password:</span>
              <span className="font-mono font-bold text-foreground">verdict2026</span>
            </div>
          </div>

          <div className="flex gap-2">
            <Button
              type="button"
              variant="outline"
              size="sm"
              onClick={handleAutoFillUser}
              className="flex-1 text-xs font-semibold h-9 rounded-xl border-border hover:bg-muted"
            >
              Fill Form
            </Button>
            <Button
              type="button"
              size="sm"
              onClick={handleQuickLoginUser}
              disabled={loading}
              className="flex-1 text-xs font-bold h-9 rounded-xl bg-neutral-900 text-white hover:bg-black dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-100 shadow-sm"
            >
              1-Click Sign In
            </Button>
          </div>
        </div>

        <div className="relative flex items-center justify-center">
          <div className="border-t w-full border-border/80" />
          <span className="bg-card px-3 text-[11px] uppercase font-bold text-muted-foreground tracking-wider absolute">
            or enter credentials
          </span>
        </div>

        {/* Credentials Form */}
        <form onSubmit={handleSubmit} className="flex flex-col gap-4">
          <div className="space-y-1.5">
            <label className="text-xs font-bold text-foreground flex items-center gap-1.5">
              <Mail className="h-3.5 w-3.5 text-muted-foreground" />
              Email Address
            </label>
            <input
              type="email"
              placeholder="e.g. you@example.com"
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              required
              className="w-full rounded-xl border border-border bg-background px-4 py-2.5 text-sm font-medium text-foreground placeholder:text-muted-foreground/60 focus:ring-1 focus:ring-neutral-900 focus:outline-none dark:focus:ring-white transition-all"
            />
          </div>

          <div className="space-y-1.5">
            <label className="text-xs font-bold text-foreground flex items-center gap-1.5">
              <Lock className="h-3.5 w-3.5 text-muted-foreground" />
              Password
            </label>
            <input
              type="password"
              placeholder="Enter your password"
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              required
              className="w-full rounded-xl border border-border bg-background px-4 py-2.5 text-sm font-medium text-foreground placeholder:text-muted-foreground/60 focus:ring-1 focus:ring-neutral-900 focus:outline-none dark:focus:ring-white transition-all"
            />
          </div>

          {error && (
            <div className="p-3 rounded-xl bg-destructive/10 border border-destructive/20 text-xs font-semibold text-destructive">
              {error}
            </div>
          )}

          <Button
            type="submit"
            disabled={loading}
            size="lg"
            className="w-full mt-2 h-12 text-sm sm:text-base font-bold bg-neutral-900 text-white hover:bg-black dark:bg-white dark:text-neutral-900 dark:hover:bg-neutral-100 rounded-xl shadow-md transition-all gap-2"
          >
            {loading ? "Authenticating..." : "Sign In & Open Wardrobe"}
            <ArrowRight className="h-4 w-4" />
          </Button>
        </form>

        <div className="pt-2 text-center text-xs text-muted-foreground space-y-1">
          <p>
            Any custom email & password will automatically log in and register your personal session.
          </p>
        </div>
      </div>
    </main>
  );
}
