import type { Metadata } from "next";
import { ClerkProvider } from "@clerk/nextjs";
import { Geist, Geist_Mono } from "next/font/google";
import { ThemeProvider } from "@/components/theme/theme-provider";
import "./globals.css";

const geistSans = Geist({
  variable: "--font-geist-sans",
  subsets: ["latin"],
});

const geistMono = Geist_Mono({
  variable: "--font-geist-mono",
  subsets: ["latin"],
});

export const metadata: Metadata = {
  title: "Cortex — GitHub Codebase RAG",
  description:
    "Index, analyze, and chat with public GitHub repositories using syntax-aware chunking, hybrid retrieval, and LangGraph.",
};

export default function RootLayout({
  children,
}: {
  children: React.ReactNode;
}) {
  return (
    <ClerkProvider dynamic>
      <html
        lang="en"
        suppressHydrationWarning
        className={`${geistSans.variable} ${geistMono.variable} min-h-full antialiased`}
      >
        <head>
          {/* Anti-FOUC script: immediately resolves stored or system theme before render */}
          <script
            dangerouslySetInnerHTML={{
              __html: `
                (function() {
                  try {
                    var stored = localStorage.getItem('cortex-theme');
                    var prefersDark = window.matchMedia('(prefers-color-scheme: dark)').matches;
                    var isDark = stored ? stored === 'dark' || (stored === 'system' && prefersDark) : true;
                    if (isDark) {
                      document.documentElement.classList.add('dark');
                      document.documentElement.classList.remove('light');
                    } else {
                      document.documentElement.classList.remove('dark');
                      document.documentElement.classList.add('light');
                    }
                  } catch (e) {
                    document.documentElement.classList.add('dark');
                  }
                })();
              `,
            }}
          />
        </head>
        <body className="min-h-full flex flex-col bg-slate-50 dark:bg-zinc-950 text-slate-900 dark:text-zinc-100 selection:bg-indigo-500 selection:text-white transition-colors duration-150">
          <ThemeProvider>{children}</ThemeProvider>
        </body>
      </html>
    </ClerkProvider>
  );
}
