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
  context?: Record<string, any>;
}

export interface ChatResponse {
  message: string;
  session_id: string;
  message_id: string;
  timestamp: string;
  metadata?: Record<string, any>;
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
