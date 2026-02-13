import { clsx, type ClassValue } from "clsx";
import { twMerge } from "tailwind-merge";

export function cn(...inputs: ClassValue[]) {
  return twMerge(clsx(inputs));
}

export function formatPercent(value: number | string | null | undefined): string {
  if (value == null) return "-";
  const n = Number(value);
  if (isNaN(n)) return "-";
  return `${(n * 100).toFixed(2)}%`;
}

export function formatCurrency(
  value: number | string | null | undefined,
  market: "KR" | "US" = "KR"
): string {
  if (value == null) return "-";
  const numValue = Number(value);
  if (isNaN(numValue)) return "-";
  if (market === "KR") {
    return new Intl.NumberFormat("ko-KR", {
      style: "currency",
      currency: "KRW",
      maximumFractionDigits: 0,
    }).format(numValue);
  }
  return new Intl.NumberFormat("en-US", {
    style: "currency",
    currency: "USD",
  }).format(numValue);
}

export function formatDate(date: string | Date): string {
  return new Date(date).toLocaleDateString("ko-KR", {
    year: "numeric",
    month: "2-digit",
    day: "2-digit",
  });
}

export function formatNumber(value: number | string | null | undefined, digits = 2): string {
  if (value == null) return "-";
  const n = Number(value);
  if (isNaN(n)) return "-";
  return n.toFixed(digits);
}
