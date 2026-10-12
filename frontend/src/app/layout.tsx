import type { Metadata } from "next";
import { AuthProvider } from "@/contexts/AuthContext";
import { ThemeProvider } from "@/contexts/ThemeContext";
import { VerdictConcierge } from "@/components/VerdictConcierge";
import "./globals.css";

export const metadata: Metadata = {
  title: "Verdict | AI Purchase Decision Engine",
  description: "Cart-level counterfactual purchase decision intelligence and virtual styling engine.",
};

export default function RootLayout({ children }: { children: React.ReactNode }) {
  return (
    <html lang="en" className="light" data-theme="light" suppressHydrationWarning>
      <body className="min-h-screen bg-background text-foreground antialiased selection:bg-neutral-900 selection:text-white">
        <ThemeProvider>
          <AuthProvider>
            {children}
            <VerdictConcierge />
          </AuthProvider>
        </ThemeProvider>
      </body>
    </html>
  );
}
