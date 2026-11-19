import type { HTMLAttributes } from "react";

export type BadgeTone = "neutral" | "success" | "warning" | "danger";

export interface BaseBadgeProps extends HTMLAttributes<HTMLSpanElement> {
  tone?: BadgeTone;
}

const TONES: Record<BadgeTone, string> = {
  neutral: "bg-gray-100 text-gray-700",
  success: "bg-green-100 text-green-800",
  warning: "bg-yellow-100 text-yellow-800",
  danger: "bg-red-100 text-red-800",
};

export function BaseBadge({ tone = "neutral", className = "", children, ...rest }: BaseBadgeProps) {
  return (
    <span
      {...rest}
      className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${TONES[tone]} ${className}`}
    >
      {children}
    </span>
  );
}
