import React, { forwardRef } from "react";

export interface InputProps
  extends React.InputHTMLAttributes<HTMLInputElement> {
  label?: string;
  error?: string;
  helperText?: string;
}

export const Input = forwardRef<HTMLInputElement, InputProps>(
  ({ className = "", label, error, helperText, id, ...props }, ref) => {
    const inputId = id || (label ? label.toLowerCase().replace(/\s+/g, "-") : undefined);

    return (
      <div className="w-full">
        {label && (
          <label
            htmlFor={inputId}
            className="block text-xs font-medium text-slate-700 dark:text-zinc-300 mb-1.5"
          >
            {label}
          </label>
        )}
        <input
          id={inputId}
          ref={ref}
          className={`w-full rounded-lg border bg-white dark:bg-zinc-900/90 px-3.5 py-2 text-sm text-slate-900 dark:text-zinc-100 placeholder-slate-400 dark:placeholder-zinc-500 transition-colors focus:outline-none focus:ring-2 focus:ring-indigo-500 focus:border-indigo-500 disabled:opacity-50 disabled:cursor-not-allowed ${
            error
              ? "border-red-500 focus:border-red-500 focus:ring-red-500/20"
              : "border-slate-300 dark:border-zinc-800 hover:border-slate-400 dark:hover:border-zinc-700"
          } ${className}`}
          {...props}
        />
        {error && <p className="mt-1.5 text-xs text-red-600 dark:text-red-400">{error}</p>}
        {helperText && !error && (
          <p className="mt-1.5 text-xs text-slate-500 dark:text-zinc-500">{helperText}</p>
        )}
      </div>
    );
  }
);

Input.displayName = "Input";
