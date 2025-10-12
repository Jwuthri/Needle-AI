export interface Message {
  id: string;
  content: string;
  role: "user" | "assistant" | "system";
  timestamp: string;
  error?: boolean;
  metadata?: Record<string, any>;
}

export interface ChatMessage {
  id: string;
  content: string;
  role: "user" | "assistant" | "system";
  timestamp: string;
  error?: boolean;
  metadata?: Record<string, any>;
}

// Enhanced chat with RAG and pipeline visualization
export interface ReviewSource {
  review_id: string;
  content: string;
  author: string;
  source: string; // reddit/twitter/csv
  sentiment: number;
  url?: string;
  relevance_score: number;
}

export interface QueryPipelineStep {
  name: string; // "Query preprocessing", "Vector search", etc.
  duration_ms: number;
  status: string;
  metadata: Record<string, any>;
}

export interface EnhancedChatMessage extends ChatMessage {
  query_type?: string;
  pipeline_steps?: QueryPipelineStep[];
  sources?: ReviewSource[];
  related_questions?: string[];
}

export interface ChatSession {
  session_id: string;
  messages: Message[];
  created_at: string;
  updated_at: string;
  metadata?: Record<string, any>;
}

export interface ChatRequest {
  message: string;
  session_id?: string;
  company_id?: string;
  context?: Record<string, any>;
}

export interface ChatResponse {
  message: string;
  session_id: string;
  message_id: string;
  timestamp: string;
  metadata?: Record<string, any>;
  query_type?: string;
  pipeline_steps?: QueryPipelineStep[];
  sources?: ReviewSource[];
  related_questions?: string[];
}

export interface WebSocketMessage {
  type: "user_message" | "ai_message" | "user_joined" | "user_left" | "error";
  message?: Message;
  session_id?: string;
  total_connections?: number;
  error?: string;
  data?: any;
}

export interface ChatConfig {
  maxMessageLength: number;
  maxMessagesPerSession: number;
  enableMarkdown: boolean;
  enableFileUploads: boolean;
  allowedFileTypes: string[];
  maxFileSize: number;
}
