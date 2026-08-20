"use client";

import { useEffect, useState } from "react";

const API_URL = process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000";

export default function StatusPage() {
  const [status, setStatus] = useState<"loading" | "connected" | "unreachable">(
    "loading",
  );

  useEffect(() => {
    fetch(`${API_URL}/health`)
      .then((res) => res.json())
      .then((data) => {
        if (data.status === "ok") {
          setStatus("connected");
        } else {
          setStatus("unreachable");
        }
      })
      .catch(() => setStatus("unreachable"));
  }, []);

  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-3xl font-bold">System Status</h1>
      <div className="flex items-center gap-2">
        <span
          className={`h-3 w-3 rounded-full ${
            status === "loading"
              ? "bg-yellow-400"
              : status === "connected"
                ? "bg-green-500"
                : "bg-red-500"
          }`}
        />
        <span className="text-lg">
          Backend:{" "}
          {status === "loading"
            ? "Checking…"
            : status === "connected"
              ? "Connected"
              : "Unreachable"}
        </span>
      </div>
      <a href="/" className="mt-4 text-sm text-blue-600 underline">
        ← Back home
      </a>
    </main>
  );
}
