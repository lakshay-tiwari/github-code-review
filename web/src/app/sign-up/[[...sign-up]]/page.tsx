import { SignUp } from "@clerk/nextjs";
import Link from "next/link";
import { ArrowLeft } from "lucide-react";

export default function SignUpPage() {
  return (
    <div className="flex min-h-screen flex-col items-center justify-center bg-zinc-950 px-4 py-12 sm:px-6 lg:px-8">
      <div className="mb-8">
        <Link
          href="/"
          className="inline-flex items-center gap-2 text-xs text-zinc-400 transition-colors hover:text-zinc-200"
        >
          <ArrowLeft className="h-4 w-4" />
          <span>Back to Cortex</span>
        </Link>
      </div>

      <div className="w-full max-w-md">
        <SignUp
          appearance={{
            elements: {
              rootBox: "w-full",
              card: "bg-zinc-900/90 border border-zinc-800 text-zinc-100 shadow-2xl backdrop-blur-md",
              headerTitle: "text-zinc-100",
              headerSubtitle: "text-zinc-400",
              socialButtonsBlockButton:
                "border border-zinc-700 bg-zinc-800/80 text-zinc-200 hover:bg-zinc-800 hover:text-white",
              socialButtonsBlockButtonText: "text-zinc-200 font-medium",
              dividerLine: "bg-zinc-800",
              dividerText: "text-zinc-400",
              formFieldLabel: "text-zinc-300",
              formFieldInput:
                "bg-zinc-950 border-zinc-700 text-zinc-100 focus:border-indigo-500 focus:ring-1 focus:ring-indigo-500",
              formButtonPrimary:
                "bg-indigo-600 hover:bg-indigo-500 text-white font-medium shadow-md shadow-indigo-600/20",
              footerActionLink: "text-indigo-400 hover:text-indigo-300",
            },
          }}
        />
      </div>
    </div>
  );
}
