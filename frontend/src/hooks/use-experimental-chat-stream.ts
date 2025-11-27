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
  const currentContentRef = useRef<string>('');
  const seenAgentsRef = useRef<Set<string>>(new Set()); // Track agents we've seen to prevent duplicates
  const currentAgentRef = useRef<string | null>(null); // Track current agent for tool attribution

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
      currentContentRef.current = '';
      seenAgentsRef.current = new Set(); // Reset seen agents for new message
      currentAgentRef.current = null;

      // Create abort controller for cancellation
      abortControllerRef.current = new AbortController();

      try {
        const headers: Record<string, string> = {
          'Content-Type': 'application/json',
        };

        if (authToken) {
          headers['Authorization'] = `Bearer ${authToken}`;
        }

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

          const decoded = decoder.decode(value, { stream: true });
          buffer += decoded;

          const lines = buffer.split('\n');
          buffer = lines.pop() || '';

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
                    const agentData = update.data as { agent_name: string; status?: string };
                    const agentName = agentData.agent_name;
                    
                    // Skip if we've already seen this agent (prevent duplicates)
                    if (seenAgentsRef.current.has(agentName)) {
                      // Just update current agent tracking without creating new step
                      currentAgentRef.current = agentName;
                      setCurrentAgent(agentName);
                      break;
                    }
                    
                    // Mark this agent as seen
                    seenAgentsRef.current.add(agentName);
                    
                    // Save current content to previous active step before switching
                    const savedContent = currentContentRef.current;
                    
                    setAgentSteps((prev) => {
                      // Mark previous active text steps as completed with their content
                      const completedPrev = prev.map(s => {
                        if (s.status === 'active' && !s.is_structured) {
                          return { 
                            ...s, 
                            status: 'completed' as const, 
                            content: s.content || savedContent || ''
                          };
                        }
                        return s;
                      });
                      
                      // Create new step for this agent
                      return [
                        ...completedPrev,
                        {
                          step_id: `agent-${agentName}-${Date.now()}`,
                          agent_name: agentName,
                          content: '',
                          is_structured: false,
                          timestamp: new Date().toISOString(),
                          status: 'active' as const,
                          step_order: stepCounter,
                        },
                      ];
                    });
                    
                    currentAgentRef.current = agentName;
                    setCurrentAgent(agentName);
                    setCurrentContent('');
                    currentContentRef.current = '';
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
                      tool: string;
                      input: any;
                    };
                    
                    setActiveToolCalls([]);
                    
                    const toolAgent = currentAgentRef.current || 'workflow';
                    
                    setToolExecutions((prev) => [
                      ...prev,
                      {
                        tool_name: toolCallData.tool,
                        tool_kwargs: toolCallData.input,
                        agent_name: toolAgent,
                        status: 'running',
                      },
                    ]);

                    const toolCallStepId = `tool-${toolCallData.tool}-${Date.now()}`;
                    setAgentSteps((prev) => [
                      ...prev,
                      {
                        step_id: toolCallStepId,
                        agent_name: toolAgent,
                        content: {
                          tool_name: toolCallData.tool,
                          tool_kwargs: toolCallData.input,
                          type: 'tool_call',
                        },
                        is_structured: true,
                        timestamp: new Date().toISOString(),
                        status: 'active' as const,
                        step_order: stepCounter,
                      },
                    ]);
                    stepCounter++;
                    break;

                  case 'tool_result':
                    const toolResultData = update.data as {
                      tool: string;
                      output?: string;
                    };
                    
                    setToolExecutions((prev) =>
                      prev.map((exec) =>
                        exec.tool_name === toolResultData.tool && exec.status === 'running'
                          ? { ...exec, output: toolResultData.output, status: 'completed' }
                          : exec
                      )
                    );

                    // Find and update the matching tool call step
                    setAgentSteps((prev) => {
                      const newSteps = [...prev];
                      // Search from end for the most recent matching active tool
                      for (let i = newSteps.length - 1; i >= 0; i--) {
                        const step = newSteps[i];
                        if (step.is_structured && 
                            step.status === 'active' && 
                            step.content?.tool_name === toolResultData.tool) {
                          newSteps[i] = {
                            ...step,
                            status: 'completed' as const,
                            raw_output: toolResultData.output,
                          };
                          break;
                        }
                      }
                      return newSteps;
                    });
                    break;

                  case 'content':
                    const chunk = update.data.content;
                    setThinkingText('');
                    setActiveToolCalls([]);
                    
                    // Accumulate content
                    setCurrentContent((prev) => {
                      const newContent = prev + chunk;
                      currentContentRef.current = newContent;
                      return newContent;
                    });
                    
                    // Update the current agent's active step with content
                    setAgentSteps((prevSteps) => {
                      const newSteps = [...prevSteps];
                      // Find the last active non-structured step
                      for (let i = newSteps.length - 1; i >= 0; i--) {
                        if (newSteps[i].status === 'active' && !newSteps[i].is_structured) {
                          newSteps[i] = {
                            ...newSteps[i],
                            content: currentContentRef.current
                          };
                          break;
                        }
                      }
                      return newSteps;
                    });
                    
                    options.onContentChunk?.(chunk);
                    break;

                  case 'complete':
                    const finalResponse = update.data as ChatResponse;
                    const finalContent = currentContentRef.current;
                    
                    // Mark all remaining active steps as completed
                    setAgentSteps((prev) => 
                      prev.map((step) => {
                        if (step.status === 'active') {
                          if (!step.is_structured && finalContent) {
                            return { ...step, status: 'completed' as const, content: step.content || finalContent };
                          }
                          return { ...step, status: 'completed' as const };
                        }
                        return step;
                      })
                    );
                    
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
    agentSteps,
    currentAgent,
    status,
    toolExecutions,
    thinkingText,
    activeToolCalls,
  };
}

