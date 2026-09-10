import Link from "next/link";

export default function Home() {
  return (
    <main className="flex min-h-screen flex-col items-center justify-center gap-4 p-8">
      <h1 className="text-4xl font-bold">Verdict</h1>
      <p className="text-lg text-muted-foreground">AI Purchase Decision Engine</p>
      <div className="flex gap-4">
        <Link
          href="/status"
          className="rounded bg-blue-600 px-4 py-2 text-white hover:bg-blue-700"
        >
          System Status
        </Link>
        <Link
          href="/login"
          className="rounded border px-4 py-2 hover:bg-gray-100"
        >
          Log In
        </Link>
        <Link
          href="/signup"
          className="rounded border px-4 py-2 hover:bg-gray-100"
        >
          Sign Up
        </Link>
        <Link
          href="/dashboard"
          className="rounded border px-4 py-2 hover:bg-gray-100"
        >
          Dashboard
        </Link>
        <Link
          href="/stylist"
          className="rounded bg-indigo-600 px-4 py-2 text-white hover:bg-indigo-700"
        >
          Stylist Chat
        </Link>
      </div>
    </main>
  );
}
