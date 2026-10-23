import React, { forwardRef } from "react";

export interface ButtonProps
  extends React.ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "outline" | "ghost" | "danger";
  size?: "sm" | "md" | "lg";
  isLoading?: boolean;
}

export const Button = forwardRef<HTMLButtonElement, ButtonProps>(
  (
    {
      className = "",
      variant = "primary",
      size = "md",
      isLoading = false,
      disabled,
      children,
      ...props
    },
    ref
  ) => {
    const baseStyles =
      "inline-flex items-center justify-center font-medium rounded-lg transition-colors focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-indigo-500 focus-visible:ring-offset-2 focus-visible:ring-offset-white dark:focus-visible:ring-offset-zinc-950 disabled:opacity-50 disabled:pointer-events-none select-none cursor-pointer";

    const variantStyles = {
      primary:
        "bg-indigo-600 text-white hover:bg-indigo-500 shadow-sm shadow-indigo-600/25 active:bg-indigo-700",
      secondary:
        "bg-slate-100 text-slate-800 hover:bg-slate-200 border border-slate-200/80 dark:bg-zinc-800 dark:text-zinc-100 dark:hover:bg-zinc-700 dark:border-zinc-700/60",
      outline:
        "border border-slate-300 text-slate-700 hover:bg-slate-100 hover:text-slate-900 dark:border-zinc-700 dark:text-zinc-300 dark:hover:bg-zinc-800 dark:hover:text-white",
      ghost:
        "text-slate-600 hover:text-slate-900 hover:bg-slate-100 dark:text-zinc-400 dark:hover:text-zinc-100 dark:hover:bg-zinc-800/60",
      danger: "bg-red-600 text-white hover:bg-red-500",
    };

    const sizeStyles = {
      sm: "h-8 px-3 text-xs gap-1.5",
      md: "h-9 px-4 text-sm gap-2",
      lg: "h-11 px-6 text-base gap-2.5",
    };

    return (
      <button
        ref={ref}
        disabled={disabled || isLoading}
        className={`${baseStyles} ${variantStyles[variant]} ${sizeStyles[size]} ${className}`}
        {...props}
      >
        {isLoading && (
          <svg
            className="animate-spin -ml-0.5 h-4 w-4 text-current"
            xmlns="http://www.w3.org/2000/svg"
            fill="none"
            viewBox="0 0 24 24"
            aria-hidden="true"
          >
            <circle
              className="opacity-25"
              cx="12"
              cy="12"
              r="10"
              stroke="currentColor"
              strokeWidth="4"
            />
            <path
              className="opacity-75"
              fill="currentColor"
              d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z"
            />
          </svg>
        )}
        {children}
      </button>
    );
  }
);

Button.displayName = "Button";
