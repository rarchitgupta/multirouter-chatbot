"use client";

import type { Overview } from "@/lib/analytics";

function fmt(n: number) {
  if (n >= 1_000_000) return `${(n / 1_000_000).toFixed(1)}M`;
  if (n >= 1_000) return `${(n / 1_000).toFixed(1)}k`;
  return String(n);
}

function Card({ label, value, sub }: { label: string; value: string | number; sub?: string }) {
  return (
    <div className="rounded-lg border bg-card p-4">
      <p className="text-xs text-muted-foreground">{label}</p>
      <p className="mt-1 text-2xl font-semibold tabular-nums">{value}</p>
      {sub && <p className="mt-0.5 text-xs text-muted-foreground">{sub}</p>}
    </div>
  );
}

function Skeleton() {
  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="h-3 w-24 animate-pulse rounded bg-muted" />
      <div className="mt-2 h-7 w-16 animate-pulse rounded bg-muted" />
    </div>
  );
}

export function OverviewCards({ data, isLoading }: { data: Overview | undefined; isLoading: boolean }) {
  if (isLoading || !data) {
    return (
      <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
        {Array.from({ length: 6 }).map((_, i) => <Skeleton key={i} />)}
      </div>
    );
  }
  return (
    <div className="grid grid-cols-2 gap-4 sm:grid-cols-3 lg:grid-cols-6">
      <Card label="Conversations" value={fmt(data.total_conversations)} />
      <Card label="Messages" value={fmt(data.total_messages)} />
      <Card label="LLM Requests" value={fmt(data.total_requests)} />
      <Card label="Tokens Used" value={fmt(data.total_tokens)} />
      <Card label="Avg Latency" value={data.avg_latency_ms != null ? `${Math.round(data.avg_latency_ms)} ms` : "—"} />
      <Card label="Error Rate" value={`${(data.error_rate * 100).toFixed(1)}%`} sub={data.error_rate > 0.05 ? "⚠ above 5%" : undefined} />
    </div>
  );
}
