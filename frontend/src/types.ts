export type Citation = {
  chunk_id: string;
  document_id: string;
  document_name: string;
  excerpt: string;
  score: number;
};

export type ToolCall = {
  name: string;
  arguments: Record<string, unknown>;
  status: "completed" | "approval_required" | "failed";
  result?: Record<string, unknown>;
  action_id?: string;
};

export type ChatResponse = {
  conversation_id: string;
  answer: string;
  citations: Citation[];
  tool_calls: ToolCall[];
  latency_ms: number;
};

export type Message = {
  id: string;
  role: "user" | "assistant";
  body: string;
  response?: ChatResponse;
};

