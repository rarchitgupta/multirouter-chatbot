"use client";

import Link from "next/link";
import { useState } from "react";
import { MessageSquare } from "lucide-react";
import { type TimeRange, useErrors, useLatency, useOverview, useThroughput } from "@/lib/analytics";
import { OverviewCards } from "./overview-cards";
import { LatencyChart } from "./latency-chart";
import { ThroughputChart } from "./throughput-chart";
import { ErrorBreakdown } from "./error-breakdown";

const RANGES: { label: string; value: TimeRange }[] = [
  { label: "1 h", value: "1h" },
  { label: "24 h", value: "24h" },
  { label: "7 d", value: "7d" },
];

export default function DashboardPage() {
  const [range, setRange] = useState<TimeRange>("24h");

  const overview = useOverview();
  const latency = useLatency(range);
  const throughput = useThroughput(range);
  const errors = useErrors(range);

  return (
    <div className="flex h-dvh flex-col overflow-auto">
      <header className="flex shrink-0 items-center justify-between border-b px-6 py-3">
        <div className="flex items-center gap-4">
          <h1 className="text-base font-semibold">Dashboard</h1>
          <div className="flex gap-1 rounded-md border p-0.5 text-sm">
            {RANGES.map((r) => (
              <button
                key={r.value}
                onClick={() => setRange(r.value)}
                className={["rounded px-2.5 py-1 transition-colors", range === r.value ? "bg-foreground text-background" : "hover:bg-muted"].join(" ")}
              >
                {r.label}
              </button>
            ))}
          </div>
        </div>
        <Link href="/" className="flex items-center gap-1.5 rounded px-2.5 py-1.5 text-sm text-muted-foreground hover:bg-muted">
          <MessageSquare className="size-4" />
          Chat
        </Link>
      </header>

      <main className="flex-1 space-y-6 px-6 py-6">
        <OverviewCards data={overview.data} isLoading={overview.isLoading} />
        <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
          <LatencyChart data={latency.data} isLoading={latency.isLoading} range={range} />
          <ThroughputChart data={throughput.data} isLoading={throughput.isLoading} range={range} />
        </div>
        <ErrorBreakdown data={errors.data} isLoading={errors.isLoading} />
      </main>
    </div>
  );
}
