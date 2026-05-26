"use client";

import { useCallback, useEffect, useRef, useState, type ReactNode } from "react";
import {
  AssistantRuntimeProvider,
  useExternalStoreRuntime,
  type AppendMessage,
  type ThreadMessageLike,
} from "@assistant-ui/react";
import { listMessages, streamMessage, type Message } from "@/lib/api";

function toThreadMessage(m: Message): ThreadMessageLike {
  return {
    role: m.role,
    content: [{ type: "text", text: m.content }],
    id: m.id,
    createdAt: new Date(m.created_at),
  };
}

interface Props {
  conversationId: string | null;
  children: ReactNode;
}

export function RuntimeProvider({ conversationId, children }: Props) {
  const [messages, setMessages] = useState<Message[]>([]);
  const [isRunning, setIsRunning] = useState(false);
  const abortRef = useRef<AbortController | null>(null);

  // Load history whenever the active conversation changes.
  useEffect(() => {
    abortRef.current?.abort();
    setIsRunning(false);
    setMessages([]);
    if (!conversationId) return;
    listMessages(conversationId).then(setMessages).catch(console.error);
  }, [conversationId]);

  const onNew = useCallback(
    async (message: AppendMessage) => {
      if (!conversationId) return;
      if (message.content[0]?.type !== "text") return;
      const text = message.content[0].text;

      const tempId = crypto.randomUUID();

      setMessages((prev) => [
        ...prev,
        { id: crypto.randomUUID(), conversation_id: conversationId, role: "user", content: text, sequence_number: 0, created_at: new Date().toISOString() },
        { id: tempId, conversation_id: conversationId, role: "assistant", content: "", sequence_number: 0, created_at: new Date().toISOString() },
      ]);
      setIsRunning(true);

      const abort = new AbortController();
      abortRef.current = abort;

      try {
        await streamMessage(
          conversationId,
          text,
          {
            onDelta: (chunk) =>
              setMessages((prev) =>
                prev.map((m) => (m.id === tempId ? { ...m, content: m.content + chunk } : m)),
              ),
            onDone: (event) =>
              setMessages((prev) =>
                prev.map((m) => (m.id === tempId ? { ...m, id: event.message_id } : m)),
              ),
            onError: (err) => {
              setMessages((prev) => prev.filter((m) => m.id !== tempId));
              console.error("Stream error:", err);
            },
          },
          abort.signal,
        );
      } catch (e) {
        if ((e as Error).name !== "AbortError") {
          setMessages((prev) => prev.filter((m) => m.id !== tempId));
        }
      } finally {
        setIsRunning(false);
      }
    },
    [conversationId],
  );

  const onCancel = useCallback(async () => {
    abortRef.current?.abort();
    setIsRunning(false);
  }, []);

  const runtime = useExternalStoreRuntime({
    isRunning,
    messages,
    convertMessage: toThreadMessage,
    onNew,
    onCancel,
    setMessages: (msgs) => setMessages([...msgs] as Message[]),
  });

  return <AssistantRuntimeProvider runtime={runtime}>{children}</AssistantRuntimeProvider>;
}
