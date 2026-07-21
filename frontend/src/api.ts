import type { ChatResponse } from "./types";

export type ApprovalResponse = {
  action_id: string;
  status: "executed";
  result: Record<string, unknown>;
};

export type SystemStats = {
  documents: number;
  chunks: number;
  conversations: number;
  pending_approvals: number;
};

const API_URL = import.meta.env.VITE_API_URL ?? "http://localhost:8000";

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${API_URL}${path}`, {
    ...init,
    headers: { "Content-Type": "application/json", ...init?.headers },
  });
  if (!response.ok) {
    const payload = await response.json().catch(() => ({}));
    throw new Error(payload.detail ?? `Request failed (${response.status})`);
  }
  return response.json() as Promise<T>;
}

export function sendMessage(query: string, conversationId?: string): Promise<ChatResponse> {
  return request("/api/chat", {
    method: "POST",
    body: JSON.stringify({ query, conversation_id: conversationId, top_k: 5, method: "hybrid" }),
  });
}

export function approveAction(actionId: string, approvalToken: string): Promise<ApprovalResponse> {
  return request<ApprovalResponse>(`/api/actions/${actionId}/approve`, {
    method: "POST",
    body: JSON.stringify({ approval_token: approvalToken }),
  });
}

export function getSystemStats(): Promise<SystemStats> {
  return request<SystemStats>("/api/stats");
}

