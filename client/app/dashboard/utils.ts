import type { TimeRange } from "@/lib/analytics";

export function formatTs(ts: string, range: TimeRange): string {
  const d = new Date(ts);
  if (range === "7d") return d.toLocaleDateString([], { month: "short", day: "numeric" });
  return d.toLocaleTimeString([], { hour: "2-digit", minute: "2-digit" });
}
