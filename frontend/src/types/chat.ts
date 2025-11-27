export interface Message {
  id: string;
  content: string;
  role: "user" | "assistant" | "system";
  timestamp: string;
  completed_at?: string;
  error?: boolean;
  metadata?: Record<string, any>;
}

export interface ChatMessage {
  id: string;
  content: string;
  role: "user" | "assistant" | "system";
  timestamp: string;
  completed_at?: string;
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

export interface AgentStep {
  step_id: string;
  agent_name: string;
  content: any; // BaseModel dict or string
  is_structured: boolean;
  timestamp: string;
  status?: 'started' | 'active' | 'completed' | 'error';
  step_order?: number; // Step number in the execution sequence
  raw_output?: string; // Raw unprocessed output from agent
}

export interface ChartConfig {
  type: 'bar' | 'line' | 'pie' | 'table';
  title?: string;
  data?: {
    labels?: string[];
    datasets?: Array<{
      label?: string;
      data: number[];
      backgroundColor?: string | string[];
      borderColor?: string | string[];
      borderWidth?: number;
      fill?: boolean;
      tension?: number;
    }>;
  };
  options?: any;
  columns?: string[];
  rows?: Array<Record<string, any>>;
  totalRows?: number;
}

export interface EnhancedChatMessage extends ChatMessage {
  query_type?: string;
  pipeline_steps?: QueryPipelineStep[];
  sources?: ReviewSource[];
  related_questions?: string[];
  agent_steps?: AgentStep[];
  visualization?: ChartConfig;
  output_format?: 'text' | 'visualization' | 'cited_summary';
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
  dataset_id?: string;
  dataset_table_name?: string;
  context?: Record<string, any>;
}

export interface ChatResponse {
  message: string;
  content?: string; // Alternative to message (some endpoints use this)
  session_id?: string;
  message_id?: string;
  timestamp?: string;
  completed_at?: string;
  metadata?: Record<string, any>;
  query_type?: string;
  pipeline_steps?: QueryPipelineStep[];
  sources?: ReviewSource[];
  related_questions?: string[];
  visualization?: ChartConfig;
  output_format?: 'text' | 'visualization' | 'cited_summary';
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
