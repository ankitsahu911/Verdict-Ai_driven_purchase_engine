"use client";

import { useState, type FormEvent } from "react";
import { signInWithEmailAndPassword } from "firebase/auth";
import Link from "next/link";
import { useRouter } from "next/navigation";
import { auth } from "@/lib/firebase";
import { useAuth } from "@/contexts/AuthContext";
import { Sparkles, ShieldCheck } from "lucide-react";

export default function LoginPage() {
  const [email, setEmail] = useState("");
  const [password, setPassword] = useState("");
  const [error, setError] = useState("");
  const router = useRouter();
  const { loginAsDemo } = useAuth();

  async function handleSubmit(e: FormEvent) {
    e.preventDefault();
    setError("");
    if (!auth) { setError("Firebase not configured. Please use 1-Click Demo Login."); return; }
    try {
      await signInWithEmailAndPassword(auth, email, password);
      router.push("/dashboard");
    } catch (err: unknown) {
      setError(err instanceof Error ? err.message : "Login failed");
    }
  }

  function handleDemoLogin() {
    loginAsDemo();
    router.push("/wardrobe");
  }

  return (
    <main className="flex min-h-screen flex-col items-center justify-center p-8 bg-muted/10">
      <div className="w-full max-w-sm rounded-2xl border bg-card p-6 shadow-lg space-y-6">
        <div className="text-center space-y-1">
          <div className="inline-flex h-10 w-10 items-center justify-center rounded-xl bg-primary text-primary-foreground font-black text-xl mb-2">
            V
          </div>
          <h1 className="text-2xl font-black tracking-tight text-foreground">Log In to Verdict</h1>
          <p className="text-xs text-muted-foreground">AI Purchase Decision Engine</p>
        </div>

        {/* 1-Click Demo Login for Milestone 39 */}
        <div className="p-3.5 rounded-xl border-2 border-emerald-500/40 bg-emerald-500/10 space-y-2.5">
          <div className="flex items-center gap-2 text-emerald-700 dark:text-emerald-300 font-bold text-xs">
            <Sparkles className="h-4 w-4 shrink-0" />
            <span>Curated Demo Account</span>
          </div>
          <p className="text-[11px] text-muted-foreground leading-snug">
            Instant live presentation access to the 24-item pre-verified wardrobe with zero live AI extraction needed.
          </p>
          <button
            type="button"
            onClick={handleDemoLogin}
            className="w-full flex items-center justify-center gap-2 rounded-xl bg-emerald-600 hover:bg-emerald-700 text-white font-bold text-xs py-2.5 shadow-sm transition-all"
          >
            <ShieldCheck className="h-4 w-4" />
            <span>1-Click Demo Login (demo@verdict.engine)</span>
          </button>
        </div>

        <div className="relative flex items-center justify-center">
          <div className="border-t w-full border-muted" />
          <span className="bg-card px-2 text-[10px] uppercase font-bold text-muted-foreground absolute">
            or standard credentials
          </span>
        </div>

        <form onSubmit={handleSubmit} className="flex flex-col gap-3">
          <input
            type="email"
            placeholder="Email"
            value={email}
            onChange={(e) => setEmail(e.target.value)}
            required
            className="rounded-xl border bg-background px-3 py-2 text-xs"
          />
          <input
            type="password"
            placeholder="Password"
            value={password}
            onChange={(e) => setPassword(e.target.value)}
            required
            className="rounded-xl border bg-background px-3 py-2 text-xs"
          />
          {error && <p className="text-xs text-destructive font-medium">{error}</p>}
          <button
            type="submit"
            className="rounded-xl bg-primary px-4 py-2 text-xs font-bold text-primary-foreground hover:bg-primary/90 transition-all shadow-sm"
          >
            Log In
          </button>
        </form>

        <p className="text-center text-xs text-muted-foreground">
          No account?{" "}
          <Link href="/signup" className="text-primary font-semibold underline">
            Sign up
          </Link>
        </p>
      </div>
    </main>
  );
}
