import { useState, useCallback, useRef } from 'react';
import { ChatRequest, ChatResponse, AgentStep } from '@/types/chat';

interface StreamUpdate {
  type: 'connected' | 'status' | 'content' | 'agent_step_start' | 'agent_step_content' | 'agent_step_complete' | 'agent_stream' | 'agent_stream_structured' | 'thinking' | 'tool_call_start' | 'tool_call_param' | 'complete' | 'error';
  data: any;
}

interface AgentStepStart {
  agent_name: string;
  step_id: string;
  timestamp: string;
  step_order?: number;
}

interface AgentStepContent {
  step_id: string;
  content_chunk: string;
}

interface AgentStepComplete {
  step_id: string;
  agent_name: string;
  content: any;
  is_structured: boolean;
  step_order?: number;
}

interface UseChatStreamOptions {
  onStatusUpdate?: (status: string, message: string) => void;
  onContentChunk?: (chunk: string) => void;
  onAgentStepStart?: (data: AgentStepStart) => void;
  onAgentStepContent?: (data: AgentStepContent) => void;
  onAgentStepComplete?: (data: AgentStepComplete) => void;
  onComplete?: (response: ChatResponse) => void;
  onError?: (error: string) => void;
}

interface ToolCallState {
  tool_id: string;
  tool_name: string;
  agent_name: string | null;
  params: Record<string, any>;
}

export function useChatStream(options: UseChatStreamOptions = {}) {
  const [isStreaming, setIsStreaming] = useState(false);
  const [currentContent, setCurrentContent] = useState('');
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>([]);
  const [currentAgent, setCurrentAgent] = useState<string | null>(null);
  const [status, setStatus] = useState<{ status: string; message: string } | null>(null);
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

        // Construct full URL - use experimental endpoint for enhanced streaming
        const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1';
        const streamUrl = `${API_BASE_URL}/chat-experimental/stream`;

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
                console.log('[Stream] Full update object:', JSON.stringify(update, null, 2));

                switch (update.type) {
                  case 'connected':
                    console.log('[Stream] Connected to server');
                    break;

                  case 'status':
                    const statusData = update.data as { status: string; message: string };
                    setStatus(statusData);
                    options.onStatusUpdate?.(statusData.status, statusData.message);
                    break;

                  case 'agent_step_start':
                    const stepStart = update.data as AgentStepStart;
                    console.log('[Stream] Agent step started:', stepStart.agent_name, 'Step:', (stepStart.step_order ?? 0) + 1);
                    setCurrentAgent(stepStart.agent_name);
                    // Add new step to tracking with step order
                    setAgentSteps((prev) => [
                      ...prev,
                      {
                        step_id: stepStart.step_id,
                        agent_name: stepStart.agent_name,
                        content: '',
                        is_structured: false,
                        timestamp: stepStart.timestamp,
                        status: 'active',
                        step_order: stepStart.step_order,
                      },
                    ]);
                    options.onAgentStepStart?.(stepStart);
                    // Update status to show agent working
                    setStatus({
                      status: 'agent_working',
                      message: `🤖 Step ${(stepStart.step_order ?? 0) + 1}: ${stepStart.agent_name} is thinking...`,
                    });
                    break;

                  case 'agent_step_content':
                    const stepContent = update.data as AgentStepContent;
                    console.log('[Stream] Agent step content:', stepContent.step_id);
                    // Update the step's content buffer
                    setAgentSteps((prev) =>
                      prev.map((step) =>
                        step.step_id === stepContent.step_id
                          ? { ...step, content: (step.content || '') + stepContent.content_chunk }
                          : step
                      )
                    );
                    options.onAgentStepContent?.(stepContent);
                    break;

                  case 'agent_stream':
                    // Handle token-by-token streaming from agent (raw text)
                    const streamData = update.data;
                    const delta = streamData.delta || '';
                    console.log('[Stream] Agent stream delta:', delta);
                    // Update the currently active step with streaming text
                    setAgentSteps((prev) => {
                      const activeStepIndex = prev.findIndex(s => s.status === 'active');
                      if (activeStepIndex >= 0) {
                        const updatedSteps = [...prev];
                        const currentContent = typeof updatedSteps[activeStepIndex].content === 'string' 
                          ? updatedSteps[activeStepIndex].content 
                          : '';
                        updatedSteps[activeStepIndex] = {
                          ...updatedSteps[activeStepIndex],
                          content: currentContent + delta,
                          is_structured: false
                        };
                        return updatedSteps;
                      }
                      return prev;
                    });
                    break;

                  case 'agent_stream_structured':
                    // Handle streaming structured output (partial JSON from agent)
                    const structuredData = update.data;
                    console.log('[Stream] Streaming structured output:', structuredData.partial_content?.length || 0, 'chars');
                    // Update the currently active step with partial structured content
                    setAgentSteps((prev) => {
                      const activeStepIndex = prev.findIndex(s => s.status === 'active');
                      if (activeStepIndex >= 0) {
                        const updatedSteps = [...prev];
                        updatedSteps[activeStepIndex] = {
                          ...updatedSteps[activeStepIndex],
                          content: structuredData.partial_content,
                          is_structured: true
                        };
                        return updatedSteps;
                      }
                      return prev;
                    });
                    break;

                  case 'agent_step_complete':
                    const stepComplete = update.data as AgentStepComplete;
                    console.log('[Stream] Agent step completed:', stepComplete.agent_name);
                    // Mark step as completed with final content
                    setAgentSteps((prev) =>
                      prev.map((step) =>
                        step.step_id === stepComplete.step_id
                          ? {
                              ...step,
                              content: stepComplete.content,
                              is_structured: stepComplete.is_structured,
                              status: 'completed',
                            }
                          : step
                      )
                    );
                    setCurrentAgent(null);
                    options.onAgentStepComplete?.(stepComplete);
                    break;

                  case 'thinking':
                    const thinkingDelta = update.data.delta;
                    console.log('[Stream] Thinking delta:', thinkingDelta);
                    setThinkingText((prev) => prev + thinkingDelta);
                    break;

                  case 'tool_call_start':
                    const toolCallStart = update.data;
                    console.log('[Stream] Tool call started:', toolCallStart.tool_name);
                    setActiveToolCalls((prev) => {
                      const newState = [
                        ...prev,
                        {
                          tool_id: toolCallStart.tool_id,
                          tool_name: toolCallStart.tool_name,
                          agent_name: toolCallStart.agent_name,
                          params: {},
                        },
                      ];
                      console.log('[Stream] activeToolCalls updated:', newState);
                      return newState;
                    });
                    break;

                  case 'tool_call_param':
                    const paramUpdate = update.data;
                    console.log('[Stream] Tool call param:', paramUpdate.param_name, '=', paramUpdate.param_value);
                    setActiveToolCalls((prev) => {
                      const newState = prev.map((call) =>
                        call.tool_id === paramUpdate.tool_id
                          ? {
                              ...call,
                              params: {
                                ...call.params,
                                [paramUpdate.param_name]: paramUpdate.param_value,
                              },
                            }
                          : call
                      );
                      console.log('[Stream] activeToolCalls after param update:', newState);
                      return newState;
                    });
                    break;

                  case 'content':
                    const chunk = update.data.content;
                    console.log('[Stream] Final content chunk:', chunk.length, 'chars');
                    // Clear thinking and tool calls when final content starts
                    setThinkingText('');
                    setActiveToolCalls([]);
                    setCurrentContent((prev) => prev + chunk);
                    options.onContentChunk?.(chunk);
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
    agentSteps,
    currentAgent,
    status,
    thinkingText,
    activeToolCalls,
  };
}

