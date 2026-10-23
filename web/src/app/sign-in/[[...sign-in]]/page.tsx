import { SignIn } from "@clerk/nextjs";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";
import { ThemeToggle } from "@/components/theme/theme-toggle";

export default function SignInPage() {
  return (
    <div className="relative flex min-h-screen flex-col items-center justify-center bg-slate-50 dark:bg-zinc-950 px-4 py-12 sm:px-6 lg:px-8 transition-colors">
      <div className="absolute top-6 right-6">
        <ThemeToggle size="sm" />
      </div>

      <div className="mb-8">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-xs text-slate-500 hover:text-slate-900 dark:text-zinc-400 dark:hover:text-zinc-200 transition-colors"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Cortex</span>
        </Link>
      </div>

      <div className="w-full max-w-md">
        <SignIn
          appearance={{
            elements: {
              rootBox: "w-full",
              card: "bg-white/95 dark:bg-zinc-900/90 border border-slate-200 dark:border-zinc-800 text-slate-900 dark:text-zinc-100 shadow-2xl backdrop-blur-md",
              headerTitle: "text-slate-900 dark:text-zinc-100",
              headerSubtitle: "text-slate-500 dark:text-zinc-400",
              socialButtonsBlockButton:
                "border border-slate-300 dark:border-zinc-700 bg-slate-100/80 hover:bg-slate-200 text-slate-700 dark:bg-zinc-800/80 dark:text-zinc-200 dark:hover:bg-zinc-800 dark:hover:text-white",
              socialButtonsBlockButtonText: "text-slate-700 dark:text-zinc-200 font-medium",
              dividerLine: "bg-slate-200 dark:bg-zinc-800",
              dividerText: "text-slate-400 dark:text-zinc-400",
              formFieldLabel: "text-slate-700 dark:text-zinc-300",
              formFieldInput:
                "bg-white dark:bg-zinc-950 border-slate-300 dark:border-zinc-700 text-slate-900 dark:text-zinc-100 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500",
              formButtonPrimary:
                "bg-indigo-600 hover:bg-indigo-500 text-white font-medium shadow-md shadow-indigo-600/20",
              footerActionLink: "text-indigo-600 dark:text-indigo-400 hover:text-indigo-500 dark:hover:text-indigo-300",
            },
          }}
        />
      </div>
    </div>
  );
}
