/**
 * Small inline UI primitives. Tailwind + zinc palette + Atea-red accent.
 * Drop-in shadcn-style API so components can be swapped later.
 */

import type {
  ButtonHTMLAttributes,
  InputHTMLAttributes,
  LabelHTMLAttributes,
  ReactNode,
  TextareaHTMLAttributes,
} from "react";

import { cn } from "@/lib/utils";

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: "primary" | "secondary" | "ghost" | "danger";
  size?: "sm" | "md" | "icon";
}

export function Button({
  className,
  variant = "primary",
  size = "md",
  ...props
}: ButtonProps) {
  const base =
    "inline-flex items-center justify-center gap-2 font-medium transition-all duration-150 active:scale-[0.98] disabled:cursor-not-allowed disabled:opacity-50 focus-visible:outline-none focus-visible:ring-2 focus-visible:ring-atea-500/40 focus-visible:ring-offset-2 focus-visible:ring-offset-zinc-50";
  const variants = {
    primary:
      "bg-atea-600 text-white shadow-soft hover:bg-atea-700 active:bg-atea-800",
    secondary:
      "bg-white text-zinc-800 ring-1 ring-zinc-200 shadow-soft hover:bg-zinc-50",
    ghost:
      "bg-transparent text-zinc-700 hover:bg-zinc-100",
    danger: "bg-red-600 text-white shadow-soft hover:bg-red-700",
  };
  const sizes = {
    sm: "h-8 rounded-md px-3 text-sm",
    md: "h-10 rounded-lg px-4 text-sm",
    icon: "h-10 w-10 rounded-lg p-0",
  };
  return (
    <button className={cn(base, variants[variant], sizes[size], className)} {...props} />
  );
}

export function Input({
  className,
  ...props
}: InputHTMLAttributes<HTMLInputElement>) {
  return (
    <input
      className={cn(
        "block w-full rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm placeholder:text-zinc-400 transition-colors focus:border-atea-500 focus:outline-none focus:ring-2 focus:ring-atea-500/20",
        className,
      )}
      {...props}
    />
  );
}

export function Textarea({
  className,
  ...props
}: TextareaHTMLAttributes<HTMLTextAreaElement>) {
  return (
    <textarea
      className={cn(
        "block w-full resize-none rounded-lg border border-zinc-200 bg-white px-3 py-2 text-sm placeholder:text-zinc-400 transition-colors focus:border-atea-500 focus:outline-none focus:ring-2 focus:ring-atea-500/20",
        className,
      )}
      {...props}
    />
  );
}

export function Label({
  className,
  ...props
}: LabelHTMLAttributes<HTMLLabelElement>) {
  return (
    <label
      className={cn("block text-sm font-medium text-zinc-700", className)}
      {...props}
    />
  );
}

export function Card({
  className,
  children,
}: {
  className?: string;
  children: ReactNode;
}) {
  return (
    <div
      className={cn(
        "rounded-xl border border-zinc-200/80 bg-white shadow-soft",
        className,
      )}
    >
      {children}
    </div>
  );
}

export function Badge({
  className,
  children,
  tone = "neutral",
}: {
  className?: string;
  children: ReactNode;
  tone?: "neutral" | "blue" | "green" | "amber" | "red" | "atea";
}) {
  const tones = {
    neutral: "bg-zinc-100 text-zinc-700 ring-zinc-200",
    blue: "bg-blue-50 text-blue-800 ring-blue-200",
    green: "bg-emerald-50 text-emerald-800 ring-emerald-200",
    amber: "bg-amber-50 text-amber-900 ring-amber-200",
    red: "bg-rose-50 text-rose-800 ring-rose-200",
    atea: "bg-atea-50 text-atea-700 ring-atea-200",
  };
  return (
    <span
      className={cn(
        "inline-flex items-center rounded-full px-2 py-0.5 text-[11px] font-medium ring-1 ring-inset",
        tones[tone],
        className,
      )}
    >
      {children}
    </span>
  );
}
