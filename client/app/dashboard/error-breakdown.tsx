"use client";

import type { ErrorData } from "@/lib/analytics";

function RateBar({ rate }: { rate: number }) {
  const w = Math.min(100, rate * 100);
  const color = rate > 0.1 ? "bg-red-500" : rate > 0.02 ? "bg-amber-500" : "bg-green-500";
  return (
    <div className="flex items-center gap-2">
      <div className="h-1.5 w-20 rounded-full bg-muted">
        <div className={`h-full rounded-full ${color}`} style={{ width: `${w}%` }} />
      </div>
      <span className="text-xs tabular-nums">{(rate * 100).toFixed(1)}%</span>
    </div>
  );
}

export function ErrorBreakdown({ data, isLoading }: { data: ErrorData | undefined; isLoading: boolean }) {
  if (isLoading) return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      {[0, 1].map((i) => (
        <div key={i} className="rounded-lg border bg-card p-4">
          <div className="mb-3 h-4 w-32 animate-pulse rounded bg-muted" />
          {[0, 1, 2].map((j) => <div key={j} className="mb-2 h-8 animate-pulse rounded bg-muted" />)}
        </div>
      ))}
    </div>
  );

  if (!data) return null;

  return (
    <div className="grid grid-cols-1 gap-6 lg:grid-cols-2">
      <div className="rounded-lg border bg-card p-4">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm font-medium">Errors by Provider</p>
          <span className="text-xs text-muted-foreground">{data.error_count} / {data.total} total</span>
        </div>
        {data.by_provider.length === 0 ? (
          <p className="text-sm text-muted-foreground">No requests in this window</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-xs text-muted-foreground">
                <th className="pb-2 text-left font-normal">Provider</th>
                <th className="pb-2 text-right font-normal">Requests</th>
                <th className="pb-2 text-right font-normal">Errors</th>
                <th className="pb-2 pl-4 text-left font-normal">Rate</th>
              </tr>
            </thead>
            <tbody>
              {data.by_provider.map((row) => (
                <tr key={row.provider} className="border-b last:border-0">
                  <td className="py-2 font-medium capitalize">{row.provider}</td>
                  <td className="py-2 text-right tabular-nums text-muted-foreground">{row.total}</td>
                  <td className="py-2 text-right tabular-nums">{row.error_count}</td>
                  <td className="py-2 pl-4"><RateBar rate={row.error_rate} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>

      <div className="rounded-lg border bg-card p-4">
        <div className="mb-3 flex items-center justify-between">
          <p className="text-sm font-medium">Error Types</p>
          <span className="text-xs text-muted-foreground">overall {(data.error_rate * 100).toFixed(1)}% error rate</span>
        </div>
        {data.by_type.length === 0 ? (
          <p className="text-sm text-muted-foreground">{data.error_count === 0 ? "No errors" : "No typed errors"} in this window</p>
        ) : (
          <table className="w-full text-sm">
            <thead>
              <tr className="border-b text-xs text-muted-foreground">
                <th className="pb-2 text-left font-normal">Type</th>
                <th className="pb-2 text-right font-normal">Count</th>
                <th className="pb-2 pl-4 text-left font-normal">Share</th>
              </tr>
            </thead>
            <tbody>
              {data.by_type.map((row) => (
                <tr key={row.error_type} className="border-b last:border-0">
                  <td className="py-2 font-mono text-xs">{row.error_type}</td>
                  <td className="py-2 text-right tabular-nums">{row.count}</td>
                  <td className="py-2 pl-4"><RateBar rate={data.error_count > 0 ? row.count / data.error_count : 0} /></td>
                </tr>
              ))}
            </tbody>
          </table>
        )}
      </div>
    </div>
  );
}
