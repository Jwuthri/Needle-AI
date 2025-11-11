/**
 * React Hook for N8N Chat with Real-Time Streaming
 * 
 * Handles SSE connection to backend which orchestrates n8n workflow
 * and streams agent steps in real-time.
 */

import { useState, useCallback, useRef } from 'react';

interface AgentStep {
  stepId: string;
  agentName: string;
  content: any;
  isStructured: boolean;
  stepOrder: number;
  timestamp?: string;
}

interface UseN8NChatOptions {
  sessionId: string;
  onAgentStart?: (agentName: string) => void;
  onAgentComplete?: (step: AgentStep) => void;
  onError?: (error: string) => void;
}

export function useN8NChat({ sessionId, onAgentStart, onAgentComplete, onError }: UseN8NChatOptions) {
  const [messages, setMessages] = useState<string[]>([]);
  const [agentSteps, setAgentSteps] = useState<AgentStep[]>([]);
  const [currentMessage, setCurrentMessage] = useState<string>('');
  const [isStreaming, setIsStreaming] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [executionId, setExecutionId] = useState<string | null>(null);
  
  const abortControllerRef = useRef<AbortController | null>(null);

  const sendMessage = useCallback(async (message: string, companyId?: number) => {
    setIsStreaming(true);
    setError(null);
    setCurrentMessage('');
    
    const newSteps: AgentStep[] = [];
    let responseContent = '';

    // Create new AbortController for this request
    abortControllerRef.current = new AbortController();

    try {
      const response = await fetch('/api/v1/n8n/chat/stream', {
        method: 'POST',
        headers: {
          'Content-Type': 'application/json',
        },
        body: JSON.stringify({
          message,
          session_id: sessionId,
          company_id: companyId,
        }),
        signal: abortControllerRef.current.signal,
      });

      if (!response.ok) {
        throw new Error(`HTTP error! status: ${response.status}`);
      }

      const reader = response.body?.getReader();
      if (!reader) {
        throw new Error('No response body');
      }

      const decoder = new TextDecoder();
      let buffer = '';

      while (true) {
        const { done, value } = await reader.read();
        
        if (done) break;

        buffer += decoder.decode(value, { stream: true });
        const lines = buffer.split('\n');
        
        // Keep the last incomplete line in buffer
        buffer = lines.pop() || '';

        for (const line of lines) {
          if (line.startsWith('data: ')) {
            try {
              const data = JSON.parse(line.slice(6));
              
              switch (data.type) {
                case 'connected':
                  console.log('✅ Stream connected');
                  setExecutionId(data.data.execution_id);
                  break;
                  
                case 'agent_step_start':
                  console.log(`🤖 Agent starting: ${data.data.agent_name}`);
                  onAgentStart?.(data.data.agent_name);
                  break;
                  
                case 'agent_step_complete':
                  console.log(`✅ Agent completed: ${data.data.agent_name}`);
                  const step: AgentStep = {
                    stepId: data.data.step_id,
                    agentName: data.data.agent_name,
                    content: data.data.content,
                    isStructured: data.data.is_structured,
                    stepOrder: data.data.step_order,
                    timestamp: data.data.timestamp,
                  };
                  newSteps.push(step);
                  setAgentSteps([...newSteps]);
                  onAgentComplete?.(step);
                  break;
                  
                case 'content':
                  // Stream response content
                  responseContent += data.data.content;
                  setCurrentMessage(responseContent);
                  break;
                  
                case 'complete':
                  console.log('🎉 Workflow complete');
                  setMessages(prev => [...prev, responseContent || data.data.message]);
                  setCurrentMessage('');
                  break;
                  
                case 'error':
                  console.error('❌ Error:', data.data.error);
                  const errorMsg = data.data.error;
                  setError(errorMsg);
                  onError?.(errorMsg);
                  break;
                  
                default:
                  console.log('Unknown event type:', data.type);
              }
            } catch (parseError) {
              console.error('Error parsing SSE data:', parseError);
            }
          }
        }
      }
    } catch (err: any) {
      if (err.name === 'AbortError') {
        console.log('Request aborted');
      } else {
        console.error('Stream error:', err);
        const errorMsg = err.message || 'Unknown error occurred';
        setError(errorMsg);
        onError?.(errorMsg);
      }
    } finally {
      setIsStreaming(false);
      abortControllerRef.current = null;
    }
  }, [sessionId, onAgentStart, onAgentComplete, onError]);

  const cancelStream = useCallback(() => {
    if (abortControllerRef.current) {
      abortControllerRef.current.abort();
      setIsStreaming(false);
      console.log('Stream cancelled');
    }
  }, []);

  const clearMessages = useCallback(() => {
    setMessages([]);
    setAgentSteps([]);
    setCurrentMessage('');
    setError(null);
    setExecutionId(null);
  }, []);

  return {
    messages,
    agentSteps,
    currentMessage,
    isStreaming,
    error,
    executionId,
    sendMessage,
    cancelStream,
    clearMessages,
  };
}

