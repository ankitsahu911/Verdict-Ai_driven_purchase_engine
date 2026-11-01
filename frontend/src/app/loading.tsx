export default function Loading() {
  return (
    <main className="min-h-screen bg-background px-4 py-6 sm:px-6 lg:px-8">
      <div className="mx-auto w-full max-w-7xl space-y-6 animate-pulse">
        <div className="h-16 rounded-xl border bg-card" />
        <div className="space-y-3 border-b pb-6">
          <div className="h-10 w-72 max-w-full rounded-lg bg-muted" />
          <div className="h-4 w-96 max-w-full rounded bg-muted" />
        </div>
        <div className="grid gap-4 md:grid-cols-3">
          {Array.from({ length: 3 }).map((_, index) => (
            <div key={index} className="h-48 rounded-xl border bg-card" />
          ))}
        </div>
      </div>
    </main>
  );
}
