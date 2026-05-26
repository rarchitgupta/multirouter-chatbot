"use client";

import { Area, AreaChart, CartesianGrid, Legend, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import type { LatencyData, TimeRange } from "@/lib/analytics";
import { formatTs } from "./utils";

function LatencyTooltip({ active, payload, label }: any) {
  if (!active || !payload?.length) return null;
  return (
    <div className="rounded-lg border bg-popover px-3 py-2 text-xs shadow-md">
      <p className="mb-1 font-medium text-muted-foreground">{label}</p>
      {payload.map((p: any) => (
        <p key={p.dataKey} style={{ color: p.color }}>{p.name}: {p.value != null ? `${Math.round(p.value)} ms` : "—"}</p>
      ))}
    </div>
  );
}

export function LatencyChart({ data, isLoading, range }: { data: LatencyData | undefined; isLoading: boolean; range: TimeRange }) {
  const buckets = data?.buckets.map((b) => ({ ts: formatTs(b.timestamp, range), p50: b.p50, p90: b.p90, p99: b.p99 })) ?? [];

  return (
    <div className="rounded-lg border bg-card p-4">
      <div className="mb-1 flex items-start justify-between">
        <div>
          <p className="text-sm font-medium">Latency</p>
          <p className="text-xs text-muted-foreground">P50 / P90 / P99 (ms)</p>
        </div>
        {data && (
          <p className="text-right text-xs text-muted-foreground">
            P50 {data.p50 != null ? `${Math.round(data.p50)}ms` : "—"} · P90 {data.p90 != null ? `${Math.round(data.p90)}ms` : "—"} · P99 {data.p99 != null ? `${Math.round(data.p99)}ms` : "—"}
          </p>
        )}
      </div>
      {isLoading ? (
        <div className="flex h-48 items-center justify-center"><div className="size-4 animate-spin rounded-full border-2 border-muted border-t-foreground" /></div>
      ) : buckets.length === 0 ? (
        <div className="flex h-48 items-center justify-center text-sm text-muted-foreground">No data for this window</div>
      ) : (
        <ResponsiveContainer width="100%" height={200}>
          <AreaChart data={buckets} margin={{ top: 4, right: 4, bottom: 0, left: 0 }}>
            <defs>
              {[["p50", "#6366f1"], ["p90", "#f59e0b"], ["p99", "#ef4444"]].map(([k, c]) => (
                <linearGradient key={k} id={`${k}g`} x1="0" y1="0" x2="0" y2="1">
                  <stop offset="5%" stopColor={c} stopOpacity={0.15} />
                  <stop offset="95%" stopColor={c} stopOpacity={0} />
                </linearGradient>
              ))}
            </defs>
            <CartesianGrid strokeDasharray="3 3" stroke="hsl(var(--border) / 0.5)" vertical={false} />
            <XAxis dataKey="ts" tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} />
            <YAxis tick={{ fontSize: 11, fill: "hsl(var(--muted-foreground))" }} axisLine={false} tickLine={false} tickFormatter={(v) => `${v}ms`} width={52} />
            <Tooltip content={<LatencyTooltip />} />
            <Legend iconType="circle" iconSize={6} wrapperStyle={{ fontSize: 11 }} />
            {[["p50", "P50", "#6366f1"], ["p90", "P90", "#f59e0b"], ["p99", "P99", "#ef4444"]].map(([key, name, color]) => (
              <Area key={key} type="monotone" dataKey={key} name={name} stroke={color} fill={`url(#${key}g)`} strokeWidth={1.5} dot={false} connectNulls />
            ))}
          </AreaChart>
        </ResponsiveContainer>
      )}
    </div>
  );
}
