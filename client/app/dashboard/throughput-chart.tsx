"use client";

import { Bar, BarChart, CartesianGrid, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { ThroughputData, TimeRange } from "@/lib/analytics";
import { formatTs } from "./utils";

function ThroughputTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  const d = payload[0]?.payload;
  return (
    <div className="rounded-lg border bg-popover px-3 py-2 text-xs shadow-md">
      <p className="mb-1 font-medium text-muted-foreground">{label}</p>
      <p>Requests: {d?.count ?? 0}</p>
      <p>Tokens: {(d?.tokens ?? 0).toLocaleString()}</p>
    </div>
  );
}

export function ThroughputChart({ data, isLoading, range }: { data: ThroughputData | undefined; isLoading: boolean; range: TimeRange }) {
  const buckets = data?.buckets.map((b) => ({ ts: formatTs(b.timestamp, range), count: b.count, tokens: b.tokens })) ?? [];
  const label = range === "7d" ? "day" : range === "1h" ? "minute" : "hour";

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="mb-1 flex items-start justify-between">
        <div>
          <p className="text-sm font-medium">Throughput</p>
          <p className="text-xs text-muted-foreground">Requests per {label}</p>
        </div>
        {data && <p className="text-right text-xs text-muted-foreground">{data.total_requests} requests · {data.total_tokens.toLocaleString()} tokens</p>}
      </div>
      {isLoading ? (
        <div className="flex h-48 items-center justify-center"><div className="size-4 animate-spin rounded-full border-2 border-muted border-t-foreground" /></div>
      ) : buckets.length === 0 ? (
        <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">No data for this window</div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <BarChart data={buckets} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border) / 0.5)" vertical={false} />
            <XAxis dataKey="ts" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} allowDecimals={false} width={32} />
            <Tooltip content={<ThroughputTooltip />} cursor={{ fill: "hsl(var(--muted) / 0.4)" }} />
            <Bar dataKey="count" name="Requests" fill="#6366f1" radius={[3, 3, 0, 0]} />
          </BarChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
