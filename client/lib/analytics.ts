import { useQuery } from "@tanstack/react-query";

const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function get<T>(path: string): Promise<T> {
  const res = await fetch(`${BASE}${path}`);
  if (!res.ok) throw new Error(`Analytics API ${res.status}`);
  return res.json() as Promise<T>;
}

export type TimeRange = "1h" | "24h" | "7d";

export interface Overview {
  total_conversations: number;
  total_messages: number;
  total_requests: number;
  total_tokens: number;
  avg_latency_ms: number | null;
  error_rate: number;
}

export interface LatencyBucket { timestamp: string; p50: number | null; p90: number | null; p99: number | null; avg: number | null; count: number }
export interface LatencyData { p50: number | null; p90: number | null; p99: number | null; avg: number | null; total: number; buckets: LatencyBucket[] }
export interface ThroughputBucket { timestamp: string; count: number; tokens: number; prompt_tokens: number; completion_tokens: number }
export interface ThroughputData { total_requests: number; total_tokens: number; buckets: ThroughputBucket[] }
export interface ProviderError { provider: string; total: number; error_count: number; error_rate: number }
export interface ErrorData { total: number; error_count: number; error_rate: number; by_provider: ProviderError[]; by_type: { error_type: string; count: number }[] }

function rangeParams(range: TimeRange) {
  const to = new Date();
  const from = new Date(to);
  if (range === "1h") from.setHours(from.getHours() - 1);
  else if (range === "24h") from.setHours(from.getHours() - 24);
  else from.setDate(from.getDate() - 7);
  const bucket = range === "1h" ? "minute" : range === "24h" ? "hour" : "day";
  return `from=${from.toISOString()}&to=${to.toISOString()}&bucket=${bucket}`;
}

const STALE = 30_000;

export const useOverview = () =>
  useQuery({ queryKey: ["analytics", "overview"], queryFn: () => get<Overview>("/api/v1/analytics/overview"), staleTime: STALE, refetchInterval: STALE });

export const useLatency = (range: TimeRange) =>
  useQuery({ queryKey: ["analytics", "latency", range], queryFn: () => get<LatencyData>(`/api/v1/analytics/latency?${rangeParams(range)}`), staleTime: STALE, refetchInterval: STALE });

export const useThroughput = (range: TimeRange) =>
  useQuery({ queryKey: ["analytics", "throughput", range], queryFn: () => get<ThroughputData>(`/api/v1/analytics/throughput?${rangeParams(range)}`), staleTime: STALE, refetchInterval: STALE });

export const useErrors = (range: TimeRange) =>
  useQuery({ queryKey: ["analytics", "errors", range], queryFn: () => get<ErrorData>(`/api/v1/analytics/errors?${rangeParams(range)}`), staleTime: STALE, refetchInterval: STALE });
