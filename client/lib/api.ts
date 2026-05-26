const BASE = process.env.NEXT_PUBLIC_API_URL ?? "http://localhost:8000";

async function req<T>(path: string, init?: RequestInit): Promise<T> {
  const res = await fetch(`${BASE}${path}`, {
    headers: { "Content-Type": "application/json", ...init?.headers },
    ...init,
  });
  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  return res.json() as Promise<T>;
}

// ---------------------------------------------------------------------------
// Types
// ---------------------------------------------------------------------------

export type ConversationStatus = "active" | "cancelled" | "completed";

export interface Conversation {
  id: string;
  title: string | null;
  status: ConversationStatus;
  model: string;
  provider: string;
  created_at: string;
  updated_at: string;
}

export interface Message {
  id: string;
  conversation_id: string;
  role: "user" | "assistant";
  content: string;
  sequence_number: number;
  created_at: string;
}

export interface DoneEvent {
  type: "done";
  message_id: string;
  usage: { prompt_tokens: number | null; completion_tokens: number | null; total_tokens: number | null };
  latency_ms: number;
}

// ---------------------------------------------------------------------------
// Providers
// ---------------------------------------------------------------------------

export async function getProviders(): Promise<Record<string, string[]>> {
  const data = await req<{ providers: Record<string, string[]> }>("/api/v1/providers");
  return data.providers;
}

// ---------------------------------------------------------------------------
// Conversations
// ---------------------------------------------------------------------------

export const createConversation = (provider: string, model: string) =>
  req<Conversation>("/api/v1/conversations", {
    method: "POST",
    body: JSON.stringify({ provider, model }),
  });

export const listConversations = (params?: { status?: ConversationStatus; limit?: number }) => {
  const q = new URLSearchParams();
  if (params?.status) q.set("status", params.status);
  if (params?.limit) q.set("limit", String(params.limit));
  return req<Conversation[]>(`/api/v1/conversations${q.size ? `?${q}` : ""}`);
};

export const updateConversation = (id: string, status: ConversationStatus) =>
  req<Conversation>(`/api/v1/conversations/${id}`, {
    method: "PATCH",
    body: JSON.stringify({ status }),
  });

export const deleteConversation = (id: string) =>
  fetch(`${BASE}/api/v1/conversations/${id}`, { method: "DELETE" });

// ---------------------------------------------------------------------------
// Messages
// ---------------------------------------------------------------------------

export const listMessages = (conversationId: string) =>
  req<Message[]>(`/api/v1/conversations/${conversationId}/messages`);

// ---------------------------------------------------------------------------
// Streaming
// ---------------------------------------------------------------------------

export interface StreamCallbacks {
  onDelta: (chunk: string) => void;
  onDone: (event: DoneEvent) => void;
  onError: (message: string) => void;
}

export async function streamMessage(
  conversationId: string,
  content: string,
  callbacks: StreamCallbacks,
  signal?: AbortSignal,
): Promise<void> {
  const res = await fetch(`${BASE}/api/v1/conversations/${conversationId}/messages`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ content }),
    signal,
  });

  if (!res.ok) {
    const text = await res.text().catch(() => res.statusText);
    throw new Error(`API ${res.status}: ${text}`);
  }
  if (!res.body) throw new Error("No response body");

  const reader = res.body.getReader();
  const decoder = new TextDecoder();
  let buffer = "";

  try {
    while (true) {
      const { done, value } = await reader.read();
      if (done) break;
      buffer += decoder.decode(value, { stream: true });
      const blocks = buffer.split("\n\n");
      buffer = blocks.pop() ?? "";

      for (const block of blocks) {
        const dataLine = block.split("\n").find((l) => l.startsWith("data: "));
        if (!dataLine) continue;
        try {
          const event = JSON.parse(dataLine.slice(6));
          if (event.type === "delta") callbacks.onDelta(event.content);
          else if (event.type === "done") callbacks.onDone(event);
          else if (event.type === "error") callbacks.onError(event.message);
        } catch { /* skip malformed */ }
      }
    }
  } finally {
    reader.releaseLock();
  }
}
