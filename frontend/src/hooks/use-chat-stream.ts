import { useState, useCallback, useRef } from 'react';
import { ChatRequest, ChatResponse, ExecutionTreeData } from '@/types/chat';

interface StreamUpdate {
  type: 'connected' | 'status' | 'content' | 'tree_update' | 'complete' | 'error' | 'tool_call_started' | 'tool_call_completed';
  data: any;
}

interface ToolCallStarted {
  agent_id: string;
  tool_name: string;
  tool_args: Record<string, any>;
  node_id: string;
}

interface ToolCallCompleted {
  tool_name: string;
  result: string | null;
}

interface UseChatStreamOptions {
  onStatusUpdate?: (status: string, message: string) => void;
  onContentChunk?: (chunk: string) => void;
  onTreeUpdate?: (tree: ExecutionTreeData) => void;
  onToolCallStarted?: (data: ToolCallStarted) => void;
  onToolCallCompleted?: (data: ToolCallCompleted) => void;
  onComplete?: (response: ChatResponse) => void;
  onError?: (error: string) => void;
}

export function useChatStream(options: UseChatStreamOptions = {}) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentContent, setCurrentContent] = useState('');
  const [currentTree, setCurrentTree] = useState<ExecutionTreeData | null>(null);
  const [status, setStatus] = useState<{ status: string; message: string } | null>(null);
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (request: ChatRequest, authToken?: string | null) => {
      setIsStreaming(true);
      setCurrentContent('');
      setCurrentTree(null);
      setStatus(null);

      // Create abort controller for cancellation
      abortControllerRef.current = new AbortController();

      try {
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
        };

        // Add auth token if provided
        if (authToken) {
          headers['Authorization'] = `Bearer ${authToken}`;
        }

        // Construct full URL - don't use relative path to avoid double /api/v1
        const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
        const streamUrl = `${API_BASE_URL}/chat/stream`;

        console.log('[Stream] Initiating stream request to:', streamUrl);
        console.log('[Stream] Request:', request);

        const response = await fetch(streamUrl, {
          method: 'POST',
          headers,
          body: JSON.stringify(request),
          signal: abortControllerRef.current.signal,
        });

        console.log('[Stream] Response status:', response.status);

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        console.log('[Stream] Starting to read stream...');

        if (!reader) {
          throw new Error('Response body is not readable');
        }

        let buffer = '';
        let chunkCount = 0;

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            console.log('[Stream] Stream ended. Total chunks received:', chunkCount);
            break;
          }

          chunkCount++;
          // Decode chunk and add to buffer
          const decoded = decoder.decode(value, { stream: true });
          buffer += decoded;
          console.log(`[Stream] Chunk #${chunkCount}: ${decoded.length} bytes`);

          // Process complete SSE messages
          const lines = buffer.split('\n');
          buffer = lines.pop() || ''; // Keep incomplete line in buffer

          for (const line of lines) {
            if (line.startsWith('data: ')) {
              const data = line.slice(6);
              if (data === '[DONE]') {
                continue;
              }

              try {
                const update: StreamUpdate = JSON.parse(data);
                console.log('[Stream] Received update:', update.type, update.data);

                switch (update.type) {
                  case 'connected':
                    console.log('[Stream] Connected to server');
                    break;

                  case 'status':
                    const statusData = update.data as { status: string; message: string };
                    setStatus(statusData);
                    options.onStatusUpdate?.(statusData.status, statusData.message);
                    break;

                  case 'content':
                    const chunk = update.data.content;
                    console.log('[Stream] Content chunk:', chunk.length, 'chars');
                    setCurrentContent((prev) => prev + chunk);
                    options.onContentChunk?.(chunk);
                    break;

                  case 'tree_update':
                    const tree = update.data as ExecutionTreeData;
                    setCurrentTree(tree);
                    options.onTreeUpdate?.(tree);
                    break;

                  case 'tool_call_started':
                    const toolStarted = update.data as ToolCallStarted;
                    options.onToolCallStarted?.(toolStarted);
                    // Update status to show tool being called
                    setStatus({
                      status: 'tool_call',
                      message: `🔧 ${toolStarted.agent_id} calling ${toolStarted.tool_name}...`
                    });
                    break;

                  case 'tool_call_completed':
                    const toolCompleted = update.data as ToolCallCompleted;
                    options.onToolCallCompleted?.(toolCompleted);
                    break;

                  case 'complete':
                    const finalResponse = update.data as ChatResponse;
                    options.onComplete?.(finalResponse);
                    break;

                  case 'error':
                    const error = update.data.error;
                    options.onError?.(error);
                    throw new Error(error);
                }
              } catch (parseError) {
                console.error('Failed to parse SSE data:', parseError);
              }
            }
          }
        }
      } catch (error) {
        if (error instanceof Error) {
          if (error.name === 'AbortError') {
            console.log('Stream aborted by user');
          } else {
            console.error('Stream error:', error);
            options.onError?.(error.message);
          }
        }
      } finally {
        setIsStreaming(false);
        abortControllerRef.current = null;
      }
    },
    [options]
  );

  const stopStreaming = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      abortControllerRef.current = null;
    }
  }, []);

  return {
    sendMessage,
    stopStreaming,
    isStreaming,
    currentContent,
    currentTree,
    status,
  };
}

