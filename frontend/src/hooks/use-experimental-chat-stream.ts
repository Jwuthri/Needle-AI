import { useState, useCallback, useRef } from 'react';
import { ChatRequest, ChatResponse, AgentStep } from '@/types/chat';

interface StreamUpdate {
  type: 'status' | 'agent' | 'tool_call' | 'tool_result' | 'content' | 'complete' | 'error' | 'thinking' | 'tool_call_start' | 'tool_call_param';
  data: any;
}

interface ToolExecution {
  tool_name: string;
  tool_kwargs: any;
  output?: any;
  status: 'running' | 'completed';
  agent_name?: string;
}

interface ToolCallState {
  tool_id: string;
  tool_name: string;
  agent_name: string | null;
  params: Record<string, any>;
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
  const [thinkingText, setThinkingText] = useState('');
  const [activeToolCalls, setActiveToolCalls] = useState<ToolCallState[]>([]);
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(
    async (request: ChatRequest, authToken?: string | null) => {
      setIsStreaming(true);
      setCurrentContent('');
      setAgentSteps([]);
      setCurrentAgent(null);
      setStatus(null);
      setToolExecutions([]);
      setThinkingText('');
      setActiveToolCalls([]);

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

        const response = await fetch(streamUrl, {
          method: 'POST',
          headers,
          body: JSON.stringify(request),
          signal: abortControllerRef.current.signal,
        });

        if (!response.ok) {
          throw new Error(`HTTP error! status: ${response.status}`);
        }

        const reader = response.body?.getReader();
        const decoder = new TextDecoder();

        if (!reader) {
          throw new Error('Response body is not readable');
        }

        let buffer = '';
        let stepCounter = 0;

        while (true) {
          const { done, value } = await reader.read();

          if (done) {
            break;
          }
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

                switch (update.type) {
                  case 'status':
                    const statusData = update.data as { message: string };
                    setStatus({ status: 'working', message: statusData.message });
                    options.onStatusUpdate?.('working', statusData.message);
                    break;

                  case 'agent':
                    const agentData = update.data as { agent_name: string };
                    const agentName = agentData.agent_name;
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

                  case 'thinking':
                    const thinkingDelta = update.data.delta;
                    setThinkingText((prev) => prev + thinkingDelta);
                    break;

                  case 'tool_call_start':
                    const toolCallStart = update.data;
                    setActiveToolCalls((prev) => [
                      ...prev,
                      {
                        tool_id: toolCallStart.tool_id,
                        tool_name: toolCallStart.tool_name,
                        agent_name: toolCallStart.agent_name,
                        params: {},
                      },
                    ]);
                    break;

                  case 'tool_call_param':
                    const paramUpdate = update.data;
                    setActiveToolCalls((prev) =>
                      prev.map((call) =>
                        call.tool_id === paramUpdate.tool_id
                          ? {
                              ...call,
                              params: {
                                ...call.params,
                                [paramUpdate.param_name]: paramUpdate.param_value,
                              },
                            }
                          : call
                      )
                    );
                    break;

                  case 'tool_call':
                    const toolCallData = update.data as {
                      tool_name: string;
                      tool_kwargs: any;
                      agent_name?: string;
                    };
                    
                    // Clear active tool calls (finalized)
                    setActiveToolCalls([]);
                    
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
                      output?: any;
                      raw_output?: string;
                      is_error?: boolean;
                    };
                    const resultStatus = toolResultData.is_error ? 'error' : 'completed';
                    
                    // Update tool execution tracking
                    setToolExecutions((prev) =>
                      prev.map((exec) =>
                        exec.tool_name === toolResultData.tool_name && exec.status === 'running'
                          ? { ...exec, output: toolResultData.raw_output || toolResultData.output, status: 'completed' }
                          : exec
                      )
                    );

                    // Update the last step with output and status
                    setAgentSteps((prev) => {
                      const lastStep = prev[prev.length - 1];
                      if (lastStep && lastStep.content?.tool_name === toolResultData.tool_name) {
                        return prev.slice(0, -1).concat({
                          ...lastStep,
                          status: resultStatus,
                          content: {
                            ...lastStep.content,
                            type: 'tool_result'
                          },
                          raw_output: toolResultData.raw_output  // Use raw_output from backend
                        });
                      }
                      return prev;
                    });
                    
                    stepCounter++;
                    break;

                  case 'content':
                    const chunk = update.data.content;
                    // Clear thinking and tool calls when final content starts
                    setThinkingText('');
                    setActiveToolCalls([]);
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
    thinkingText,
    activeToolCalls,
  };
}

