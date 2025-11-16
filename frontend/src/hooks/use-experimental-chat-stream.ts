import { useState, useCallback, useRef } from 'react';
import { ChatRequest, ChatResponse, AgentStep } from '@/types/chat';

interface StreamUpdate {
  type: 'status' | 'agent' | 'tool_call' | 'tool_result' | 'content' | 'complete' | 'error';
  data: any;
}

interface ToolExecution {
  tool_name: string;
  tool_kwargs: any;
  output?: any;
  status: 'running' | 'completed';
  agent_name?: string;
}

interface UseExperimentalChatStreamOptions {
  onStatusUpdate?: (status: string, message: string) => void;
  onContentChunk?: (chunk: string) => void;
  onComplete?: (response: ChatResponse) => void;
  onError?: (error: string) => void;
}

export function useExperimentalChatStream(options: UseExperimentalChatStreamOptions = {}) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentContent, setCurrentContent] = useState('');
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>([]);
  const [currentAgent, setCurrentAgent] = useState<string | null>(null);
  const [status, setStatus] = useState<{ status: string; message: string } | null>(null);
  const [toolExecutions, setToolExecutions] = useState<ToolExecution[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (request: ChatRequest, authToken?: string | null) => {
      setIsStreaming(true);
      setCurrentContent('');
      setAgentSteps([]);
      setCurrentAgent(null);
      setStatus(null);
      setToolExecutions([]);

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

        // Construct full URL for experimental endpoint
        const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
        const streamUrl = `${API_BASE_URL}/chat-experimental/stream`;

        console.log('[Experimental Stream] Initiating stream request to:', streamUrl);
        console.log('[Experimental Stream] Request:', request);

        const response = await fetch(streamUrl, {
          method: 'POST',
          headers,
          body: JSON.stringify(request),
          signal: abortControllerRef.current.signal,
        });

        console.log('[Experimental Stream] Response status:', response.status);

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        console.log('[Experimental Stream] Starting to read stream...');

        if (!reader) {
          throw new Error('Response body is not readable');
        }

        let buffer = '';
        let chunkCount = 0;
        let stepCounter = 0;

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            console.log('[Experimental Stream] Stream ended. Total chunks received:', chunkCount);
            break;
          }

          chunkCount++;
          // Decode chunk and add to buffer
          const decoded = decoder.decode(value, { stream: true });
          buffer += decoded;

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
                console.log('[Experimental Stream] Received update:', update.type, update.data);

                switch (update.type) {
                  case 'status':
                    const statusData = update.data as { message: string };
                    setStatus({ status: 'working', message: statusData.message });
                    options.onStatusUpdate?.('working', statusData.message);
                    break;

                  case 'agent':
                    const agentData = update.data as { agent_name: string };
                    const agentName = agentData.agent_name;
                    console.log('[Experimental Stream] Agent transition:', agentName);
                    setCurrentAgent(agentName);
                    
                    // Add agent step
                    const agentStepId = `agent-${Date.now()}-${stepCounter}`;
                    setAgentSteps((prev) => [
                      ...prev,
                      {
                        step_id: agentStepId,
                        agent_name: agentName,
                        content: `Agent: ${agentName}`,
                        is_structured: false,
                        timestamp: new Date().toISOString(),
                        status: 'active',
                        step_order: stepCounter,
                      },
                    ]);
                    stepCounter++;
                    break;

                  case 'tool_call':
                    const toolCallData = update.data as {
                      tool_name: string;
                      tool_kwargs: any;
                      agent_name?: string;
                    };
                    console.log('[Experimental Stream] Tool call:', toolCallData.tool_name);
                    
                    // Add tool execution tracking
                    setToolExecutions((prev) => [
                      ...prev,
                      {
                        tool_name: toolCallData.tool_name,
                        tool_kwargs: toolCallData.tool_kwargs,
                        agent_name: toolCallData.agent_name,
                        status: 'running',
                      },
                    ]);

                    // Add tool call as agent step
                    const toolCallStepId = `tool-call-${Date.now()}-${stepCounter}`;
                    setAgentSteps((prev) => [
                      ...prev,
                      {
                        step_id: toolCallStepId,
                        agent_name: toolCallData.agent_name || currentAgent || 'workflow',
                        content: {
                          tool_name: toolCallData.tool_name,
                          tool_kwargs: toolCallData.tool_kwargs,
                          type: 'tool_call',
                        },
                        is_structured: true,
                        timestamp: new Date().toISOString(),
                        status: 'active',
                        step_order: stepCounter,
                      },
                    ]);
                    stepCounter++;
                    break;

                  case 'tool_result':
                    const toolResultData = update.data as {
                      tool_name: string;
                      tool_kwargs: any;
                      output: any;
                    };
                    console.log('[Experimental Stream] Tool result:', toolResultData.tool_name);
                    
                    // Update tool execution tracking
                    setToolExecutions((prev) =>
                      prev.map((exec) =>
                        exec.tool_name === toolResultData.tool_name && exec.status === 'running'
                          ? { ...exec, output: toolResultData.output, status: 'completed' }
                          : exec
                      )
                    );

                    // Add tool result as agent step
                    const toolResultStepId = `tool-result-${Date.now()}-${stepCounter}`;
                    setAgentSteps((prev) => [
                      ...prev,
                      {
                        step_id: toolResultStepId,
                        agent_name: currentAgent || 'workflow',
                        content: {
                          tool_name: toolResultData.tool_name,
                          tool_kwargs: toolResultData.tool_kwargs,
                          output: toolResultData.output,
                          type: 'tool_result',
                        },
                        is_structured: true,
                        timestamp: new Date().toISOString(),
                        status: 'completed',
                        step_order: stepCounter,
                      },
                    ]);
                    stepCounter++;
                    break;

                  case 'content':
                    const chunk = update.data.content;
                    console.log('[Experimental Stream] Content chunk:', chunk.length, 'chars');
                    setCurrentContent((prev) => prev + chunk);
                    options.onContentChunk?.(chunk);
                    
                    // Mark all steps as completed when content starts streaming
                    setAgentSteps((prev) =>
                      prev.map((step) =>
                        step.status === 'active' ? { ...step, status: 'completed' } : step
                      )
                    );
                    break;

                  case 'complete':
                    const finalResponse = update.data as ChatResponse;
                    console.log('[Experimental Stream] Complete:', finalResponse);
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
    [options, currentAgent]
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
    agentSteps,
    currentAgent,
    status,
    toolExecutions,
  };
}

