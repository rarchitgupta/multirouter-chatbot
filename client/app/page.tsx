"use client";

import Link from "next/link";
import { useState } from "react";
import { BarChart2, MessageSquare, Plus, Trash2 } from "lucide-react";
import { Thread } from "@/components/assistant-ui/thread";

import { RuntimeProvider } from "@/components/runtime-provider";
import { ProviderSelector } from "@/components/provider-selector";
import {
  useConversations,
  useCreateConversation,
  useDeleteConversation,
  useUpdateConversation,
} from "@/lib/queries";
import { useProviders } from "@/lib/queries";
import type { Conversation } from "@/lib/api";

export default function Page() {
  const [conversationId, setConversationId] = useState<string | null>(null);

  const { data: providers = {} } = useProviders();
  const { data: conversations = [] } = useConversations();
  const createConversation = useCreateConversation();
  const deleteConversation = useDeleteConversation();
  const updateConversation = useUpdateConversation();

  const activeConversation = conversations.find((c) => c.id === conversationId) ?? null;

  // Pick defaults from first available provider
  const defaultProvider = Object.keys(providers)[0] ?? "";
  const defaultModel = providers[defaultProvider]?.[0] ?? "";

  const handleCreate = async () => {
    if (!defaultProvider) return;
    const conv = await createConversation.mutateAsync({ provider: defaultProvider, model: defaultModel });
    setConversationId(conv.id);
  };

  const handleProviderChange = async (provider: string, model: string) => {
    const conv = await createConversation.mutateAsync({ provider, model });
    setConversationId(conv.id);
  };

  const handleCancel = async (id: string) => {
    await updateConversation.mutateAsync({ id, status: "cancelled" });
    if (conversationId === id) setConversationId(null);
  };

  const handleDelete = async (id: string) => {
    await deleteConversation.mutateAsync(id);
    if (conversationId === id) setConversationId(null);
  };

  return (
    <RuntimeProvider conversationId={conversationId}>
      <div className="flex h-dvh overflow-hidden">
        {/* Sidebar */}
        <aside className="flex w-56 shrink-0 flex-col border-r">
          <div className="p-2">
            <button
              onClick={handleCreate}
              disabled={!defaultProvider || createConversation.isPending}
              className="flex w-full items-center gap-2 rounded-md px-2 py-1.5 text-sm font-medium hover:bg-muted disabled:opacity-50"
            >
              <Plus className="size-4" />
              {createConversation.isPending ? "Creating…" : "New conversation"}
            </button>
          </div>

          <div className="flex-1 overflow-y-auto px-2 pb-2">
            {conversations.map((c: Conversation) => (
              <div
                key={c.id}
                className={[
                  "group flex items-start justify-between gap-1 rounded-md px-2 py-1.5",
                  c.id === conversationId ? "bg-muted" : "hover:bg-muted/60",
                ].join(" ")}
              >
                <button
                  className="min-w-0 flex-1 text-left"
                  onClick={() => setConversationId(c.id)}
                >
                  <span className="block truncate text-sm">
                    {c.title ?? "Untitled"}
                  </span>
                  <span className="text-xs capitalize text-muted-foreground">
                    {c.provider} · {c.status}
                  </span>
                </button>
                <button
                  onClick={() => handleDelete(c.id)}
                  className="mt-0.5 shrink-0 opacity-0 transition-opacity group-hover:opacity-100"
                >
                  <Trash2 className="size-3.5 text-muted-foreground hover:text-destructive" />
                </button>
              </div>
            ))}
          </div>

          <div className="border-t p-2">
            <Link
              href="/dashboard"
              className="flex items-center gap-2 rounded-md px-2 py-1.5 text-sm text-muted-foreground hover:bg-muted"
            >
              <BarChart2 className="size-4" />
              Dashboard
            </Link>
          </div>
        </aside>

        {/* Chat */}
        <main className="flex flex-1 flex-col overflow-hidden">
          {conversationId && activeConversation ? (
            <>
              {/* Chat header with provider selector */}
              <div className="flex shrink-0 items-center justify-between border-b px-4 py-2">
                <div className="flex items-center gap-1.5">
                  <MessageSquare className="size-4 text-muted-foreground" />
                  <span className="text-sm font-medium truncate max-w-48">
                    {activeConversation.title ?? "Untitled"}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  {activeConversation.status === "active" && Object.keys(providers).length > 0 && (
                    <div className="flex items-center gap-1 text-xs text-muted-foreground">
                      <span>Switch to:</span>
                      <ProviderSelector
                        providers={providers}
                        value={`${activeConversation.provider}/${activeConversation.model}`}
                        onChange={handleProviderChange}
                        disabled={createConversation.isPending}
                      />
                    </div>
                  )}
                  {activeConversation.status === "active" && (
                    <button
                      onClick={() => handleCancel(conversationId)}
                      className="rounded px-2 py-1 text-xs text-muted-foreground hover:bg-muted hover:text-foreground"
                    >
                      Cancel
                    </button>
                  )}
                </div>
              </div>

              <div className="flex-1 min-h-0 overflow-hidden">
                <Thread />
              </div>
            </>
          ) : (
            <div className="flex flex-1 items-center justify-center text-sm text-muted-foreground">
              Select a conversation or create a new one
            </div>
          )}
        </main>
      </div>
    </RuntimeProvider>
  );
}
