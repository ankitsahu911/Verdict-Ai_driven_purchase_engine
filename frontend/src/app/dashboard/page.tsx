"use client";

import { useEffect, useState } from "react";
import { signOut } from "firebase/auth";
import { useRouter } from "next/navigation";
import { auth } from "@/lib/firebase";
import { apiFetch } from "@/lib/api";
import { ProtectedRoute } from "@/components/ProtectedRoute";
import { PhotoUploader } from "@/components/PhotoUploader";

interface MeResponse {
  uid: string;
  email: string;
}

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
    <main className="flex min-h-screen flex-col items-center gap-8 p-8">
      <div className="flex w-full max-w-3xl items-center justify-between">
        <h1 className="text-3xl font-bold">Dashboard</h1>
        <button
          onClick={handleLogout}
          className="rounded bg-gray-600 px-4 py-2 text-white hover:bg-gray-700"
        >
          Log out
        </button>
      </div>
      {error && <p className="text-red-500">Error: {error}</p>}
      {me && (
        <div className="w-full max-w-3xl rounded border p-4">
          <p>
            <strong>UID:</strong> {me.uid}
          </p>
          <p>
            <strong>Email:</strong> {me.email}
          </p>
        </div>
      )}
      {!me && !error && <p>Loading user info…</p>}

      <PhotoUploader />
    </main>
  );
}
