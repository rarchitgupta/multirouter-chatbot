import { useMutation, useQuery, useQueryClient } from "@tanstack/react-query";
import {
  createConversation,
  deleteConversation,
  getProviders,
  listConversations,
  listMessages,
  updateConversation,
  type Conversation,
  type ConversationStatus,
} from "@/lib/api";

export const keys = {
  providers: () => ["providers"] as const,
  conversations: () => ["conversations"] as const,
  messages: (id: string) => ["conversations", id, "messages"] as const,
};

export const useProviders = () =>
  useQuery({ queryKey: keys.providers(), queryFn: getProviders });

export const useConversations = () =>
  useQuery({ queryKey: keys.conversations(), queryFn: () => listConversations({ limit: 50 }) });

export const useMessages = (conversationId: string | null) =>
  useQuery({
    queryKey: keys.messages(conversationId ?? ""),
    queryFn: () => listMessages(conversationId!),
    enabled: !!conversationId,
  });

export const useCreateConversation = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ provider, model }: { provider: string; model: string }) =>
      createConversation(provider, model),
    onSuccess: () => qc.invalidateQueries({ queryKey: keys.conversations() }),
  });
};

export const useUpdateConversation = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: ({ id, status }: { id: string; status: ConversationStatus }) =>
      updateConversation(id, status),
    onSuccess: (updated: Conversation) => {
      qc.invalidateQueries({ queryKey: keys.conversations() });
    },
  });
};

export const useDeleteConversation = () => {
  const qc = useQueryClient();
  return useMutation({
    mutationFn: (id: string) => deleteConversation(id).then(() => {}),
    onSuccess: (_: void, id: string) => {
      qc.invalidateQueries({ queryKey: keys.conversations() });
      qc.removeQueries({ queryKey: keys.messages(id) });
    },
  });
};
