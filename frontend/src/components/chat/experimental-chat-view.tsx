'use client'

import { useState, useRef, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Sparkles, Loader, ChevronDown, ChevronUp, Wrench, CheckCircle, Zap, Play } from 'lucide-react'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'
import { TerminalInput } from './terminal-input'
import { EnhancedMessage } from './enhanced-message'
import { NeedleWelcome } from './needle-welcome'
import { EnhancedChatMessage } from '@/types/chat'
import { useExperimentalChatStream } from '@/hooks/use-experimental-chat-stream'

// Simple markdown renderer for streaming content
function StreamingMarkdown({ content }: { content: string }) {
  const lines = content.split('\n')
  const elements: JSX.Element[] = []

  lines.forEach((line, i) => {
    const trimmed = line.trim()
    
    if (trimmed.startsWith('#')) {
      const match = trimmed.match(/^(#{1,6})\s+(.+)/)
      if (match) {
        const level = match[1].length
        const text = match[2]
        const className = level === 1 ? 'text-2xl' : level === 2 ? 'text-xl' : 'text-lg'
        elements.push(
          <h3 key={i} className={`${className} font-semibold text-white mb-2 mt-2`}>
            {text}
          </h3>
        )
        return
      }
    }

    if (trimmed.startsWith('-') || trimmed.startsWith('•')) {
      const bulletMatch = trimmed.match(/^[-•]\s+(.+)/)
      if (bulletMatch) {
        elements.push(
          <div key={i} className="flex items-start mb-2">
            <span className="text-purple-400 mr-2">•</span>
            <span className="text-white/80">{bulletMatch[1]}</span>
          </div>
        )
        return
      }
    }

    if (trimmed) {
      elements.push(
        <p key={i} className="text-white/80 mb-2">
          {line}
        </p>
      )
    } else {
      elements.push(<br key={i} />)
    }
  })

  return <div className="space-y-1">{elements}</div>
}

// Format tool call or result content
function formatToolContent(content: any): JSX.Element {
  if (typeof content !== 'object') {
    return <span className="text-white/70">{String(content)}</span>
  }

  const { tool_name, tool_kwargs, output, type } = content

  return (
    <div className="space-y-2">
      {/* Tool Name */}
      <div className="flex items-center gap-2">
        <Wrench className="w-4 h-4 text-purple-400" />
        <span className="font-mono font-semibold text-purple-300">{tool_name}</span>
        {type === 'tool_call' && (
          <span className="text-xs bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded">
            Calling...
          </span>
        )}
        {type === 'tool_result' && (
          <span className="text-xs bg-green-500/20 text-green-300 px-2 py-0.5 rounded flex items-center gap-1">
            <CheckCircle className="w-3 h-3" />
            Completed
          </span>
        )}
      </div>

      {/* Tool Arguments */}
      {tool_kwargs && Object.keys(tool_kwargs).length > 0 && (
        <div className="pl-6">
          <div className="text-xs text-gray-400 mb-1">Arguments:</div>
          <div className="bg-gray-800/50 rounded p-2 text-xs font-mono">
            {Object.entries(tool_kwargs).map(([key, value]) => (
              <div key={key} className="flex gap-2">
                <span className="text-blue-400">{key}:</span>
                <span className="text-white/70">{JSON.stringify(value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tool Output */}
      {output && (
        <div className="pl-6">
          <div className="text-xs text-gray-400 mb-1">Output:</div>
          <div className="bg-gray-800/50 rounded p-2 text-xs text-white/70 max-h-40 overflow-y-auto">
            {String(output).substring(0, 500)}
            {String(output).length > 500 && '...'}
          </div>
        </div>
      )}
    </div>
  )
}

interface ExperimentalChatViewProps {
  companyId: string | null
  sessionId?: string
  onSessionIdChange?: (sessionId: string) => void
  onCompanyChange?: (companyId: string | null) => void
}

export function ExperimentalChatView({ 
  companyId, 
  sessionId, 
  onSessionIdChange, 
  onCompanyChange 
}: ExperimentalChatViewProps) {
  const { getToken } = useAuth()
  const [messages, setMessages] = useState<EnhancedChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set())
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const currentAgentStepsRef = useRef<any[]>([])
  const isSendingRef = useRef(false)

  // Use experimental streaming hook
  const {
    sendMessage: sendStreamMessage,
    isStreaming,
    currentContent,
    agentSteps,
    currentAgent,
    status: streamStatus,
    toolExecutions,
  } = useExperimentalChatStream({
    onComplete: (response) => {
      console.log('[ExperimentalChatView] onComplete called')

      const formattedSteps = currentAgentStepsRef.current.map((step) => ({
        step_id: step.step_id,
        agent_name: step.agent_name,
        content: step.content,
        is_structured: step.is_structured,
        step_order: step.step_order,
        status: 'completed' as const,
        timestamp: step.timestamp,
      }))

      const newMessage: EnhancedChatMessage = {
        id: response.message_id,
        content: response.message,
        role: 'assistant',
        timestamp: response.timestamp,
        completed_at: response.completed_at,
        metadata: response.metadata,
        agent_steps: formattedSteps,
      }

      setMessages((prev) => [...prev, newMessage])
      setIsLoading(false)

      // Auto-expand execution steps
      if (formattedSteps.length > 0) {
        setExpandedSteps((prev) => {
          const next = new Set(prev)
          next.add(response.message_id)
          return next
        })
      }
    },
    onError: (error) => {
      console.error('Streaming error:', error)
      setIsLoading(false)
    },
  })

  // Keep ref in sync
  useEffect(() => {
    currentAgentStepsRef.current = agentSteps
  }, [agentSteps])

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages, currentContent, isStreaming])

  // Load messages when session changes
  useEffect(() => {
    const loadSession = async () => {
      if (!sessionId) {
        setMessages([])
        return
      }

      // Don't reload session while sending/streaming to prevent clearing current messages
      if (isStreaming || isLoading || isSendingRef.current) {
        return
      }

      try {
        const token = await getToken()
        const api = createApiClient(token)
        const session = await api.getSession(sessionId)

        const enhancedMessages: EnhancedChatMessage[] = session.messages.map((msg) => ({
          id: msg.id,
          content: msg.content,
          role: msg.role as 'user' | 'assistant' | 'system',
          timestamp: msg.timestamp,
          completed_at: msg.completed_at,
          metadata: msg.metadata,
          agent_steps: msg.metadata?.agent_steps || [],
        }))

        setMessages(enhancedMessages)
      } catch (error) {
        console.error('Failed to load session:', error)
      }
    }

    loadSession()
  }, [sessionId, getToken, isStreaming, isLoading])

  const handleSendMessage = async (message: string) => {
    if (!message.trim()) return

    isSendingRef.current = true
    currentAgentStepsRef.current = []

    // Add user message
    const userMessage: EnhancedChatMessage = {
      id: Date.now().toString(),
      content: message,
      role: 'user',
      timestamp: new Date().toISOString(),
    }
    setMessages((prev) => [...prev, userMessage])
    setIsLoading(true)

    try {
      const token = await getToken()
      const api = createApiClient(token)

      // Create session if needed
      let currentSessionId = sessionId
      if (!currentSessionId) {
        const newSession = await api.createSession()
        currentSessionId = newSession.session_id
        if (onSessionIdChange) {
          onSessionIdChange(currentSessionId)
        }
      }

      // Use experimental streaming
      await sendStreamMessage(
        {
          message,
          session_id: currentSessionId,
          company_id: companyId || undefined,
        },
        token
      )
    } catch (error) {
      console.error('Failed to send message:', error)
      const errorMessage: EnhancedChatMessage = {
        id: Date.now().toString(),
        content: 'Sorry, I encountered an error processing your request.',
        role: 'assistant',
        timestamp: new Date().toISOString(),
        error: true,
      }
      setMessages((prev) => [...prev, errorMessage])
      setIsLoading(false)
    } finally {
      isSendingRef.current = false
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Header Badge */}
      <div className="bg-purple-900/30 border-b border-purple-500/30 px-4 py-2">
        <div className="max-w-4xl mx-auto flex items-center gap-2">
          <Zap className="w-4 h-4 text-purple-400" />
          <span className="text-sm text-purple-300 font-medium">
            Experimental Multi-Agent Workflow
          </span>
          <span className="text-xs text-purple-400/60">
            See agent steps and tool calls in real-time
          </span>
        </div>
      </div>

      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-4 sm:px-6 py-4 sm:py-6">
        <div className="max-w-4xl mx-auto space-y-6 w-full">
          {/* Welcome Message */}
          {messages.length === 0 && !isLoading && (
            <NeedleWelcome
              onPromptSelect={handleSendMessage}
              companySelected={!!companyId}
            />
          )}

          {/* Messages */}
          {messages.length > 0 && (
            <div className="space-y-6">
              {messages.map((message) => (
                <div key={message.id} className="space-y-3">
                  {/* Show execution steps above assistant messages */}
                  {message.role === 'assistant' &&
                    message.agent_steps &&
                    message.agent_steps.length > 0 && (
                      <div className="bg-gradient-to-br from-purple-900/30 via-gray-900/50 to-blue-900/30 border border-purple-500/40 rounded-xl overflow-hidden">
                        <button
                          onClick={() => {
                            setExpandedSteps((prev) => {
                              const next = new Set(prev)
                              if (next.has(message.id)) {
                                next.delete(message.id)
                              } else {
                                next.add(message.id)
                              }
                              return next
                            })
                          }}
                          className="w-full bg-gradient-to-r from-purple-500/10 to-blue-500/10 px-5 py-4 border-b border-purple-500/20 hover:from-purple-500/20 hover:to-blue-500/20 transition-all"
                        >
                          <div className="flex items-center justify-between">
                            <div className="flex items-center space-x-3">
                              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500/30 to-blue-500/30 flex items-center justify-center border border-purple-400/40">
                                <span className="text-sm font-bold text-purple-300">
                                  {message.agent_steps.length}
                                </span>
                              </div>
                              <span className="text-white font-semibold">
                                Workflow Execution
                              </span>
                            </div>
                            <div className="flex items-center space-x-2">
                              <span className="text-xs text-purple-300/70 font-mono">
                                {message.agent_steps.length} steps
                              </span>
                              {expandedSteps.has(message.id) ? (
                                <ChevronUp className="w-5 h-5 text-white/60" />
                              ) : (
                                <ChevronDown className="w-5 h-5 text-white/60" />
                              )}
                            </div>
                          </div>
                        </button>

                        {expandedSteps.has(message.id) && (
                          <div className="p-5 space-y-3">
                            {message.agent_steps.map((step, index) => (
                              <div
                                key={step.step_id}
                                className="bg-gray-800/40 border border-gray-700/40 rounded-xl p-4"
                              >
                                <div className="flex items-start justify-between mb-3">
                                  <div className="flex items-center space-x-3">
                                    <div className="w-7 h-7 rounded-lg bg-purple-500/20 text-purple-300 flex items-center justify-center font-bold text-sm">
                                      {(step.step_order ?? index) + 1}
                                    </div>
                                    <span className="text-sm font-mono text-purple-300">
                                      {step.agent_name}
                                    </span>
                                  </div>
                                </div>
                                <div className="text-sm">
                                  {step.is_structured ? (
                                    formatToolContent(step.content)
                                  ) : (
                                    <div className="text-white/80">{step.content}</div>
                                  )}
                                </div>
                              </div>
                            ))}
                          </div>
                        )}
                      </div>
                    )}

                  {/* Message */}
                  <EnhancedMessage message={message} onQuestionClick={handleSendMessage} />
                </div>
              ))}
            </div>
          )}

          {/* AI Response Area - Streaming */}
          {(isLoading || isStreaming) && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-3"
            >
              {/* Workflow Pipeline - Clean minimal style */}
              {agentSteps.length > 0 && (
                <div className="space-y-3">
                  {agentSteps.map((step, index) => (
                    <div key={step.step_id} className="flex items-start space-x-4">
                      {/* Step number */}
                      <div className="flex-shrink-0 w-6 h-6 flex items-center justify-center">
                        {step.status === 'active' ? (
                          <Loader className="w-4 h-4 animate-spin text-gray-400" />
                        ) : (
                          <span className="text-sm text-gray-500 font-medium">{index + 1}</span>
                        )}
                      </div>

                      {/* Step content */}
                      <div className="flex-1 min-w-0">
                        <div className="text-sm text-gray-300 mb-2">
                          {step.is_structured && step.content ? (
                            (() => {
                              const toolName = step.content.tool_name || step.agent_name;
                              return `Running ${toolName.replace(/_/g, ' ')}...`;
                            })()
                          ) : (
                            step.content || step.agent_name
                          )}
                        </div>

                        {/* Tool details in code block style */}
                        {step.is_structured && step.content && step.status !== 'active' && (
                          <div className="bg-gray-900/50 border border-gray-800 rounded-lg p-3 text-xs font-mono">
                            <div className="flex items-center space-x-2 mb-2">
                              <div className="w-3 h-3 bg-gray-700 rounded"></div>
                              <span className="text-gray-400">{step.content.tool_name}</span>
                            </div>
                            {step.content.tool_kwargs && (
                              <div className="text-gray-500 space-y-1">
                                {Object.entries(step.content.tool_kwargs).slice(0, 3).map(([key, value]) => (
                                  <div key={key} className="flex items-start space-x-2">
                                    <span className="text-gray-600">{key}:</span>
                                    <span className="text-gray-400 truncate">
                                      {typeof value === 'string' ? value.slice(0, 50) : JSON.stringify(value).slice(0, 50)}
                                    </span>
                                  </div>
                                ))}
                              </div>
                            )}
                          </div>
                        )}

                        {/* Timing indicator */}
                        {step.status !== 'active' && step.timestamp && (
                          <div className="flex items-center space-x-2 mt-2 text-xs text-gray-600">
                            <CheckCircle className="w-3 h-3" />
                            <span>Completed</span>
                          </div>
                        )}
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* AI Response with streaming content */}
              {(currentContent || (streamStatus && !agentSteps.length)) && (
                <div className="flex items-start space-x-3">
                  <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
                    <Sparkles className="w-4 h-4 text-white" />
                  </div>
                  <div className="flex-1">
                    {streamStatus && !agentSteps.length && !currentContent && (
                      <div className="text-xs text-purple-400 mb-2 flex items-center space-x-2">
                        <Loader className="w-3 h-3 animate-spin" />
                        <span>{streamStatus.message}</span>
                      </div>
                    )}

                    {currentContent ? (
                      <div className="text-white/90">
                        <StreamingMarkdown content={currentContent} />
                        <span className="inline-block w-2 h-4 bg-purple-400 ml-1 animate-pulse"></span>
                      </div>
                    ) : (
                      !agentSteps.length && (
                        <div className="flex space-x-1">
                          <div className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"></div>
                          <div
                            className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"
                            style={{ animationDelay: '0.1s' }}
                          ></div>
                          <div
                            className="w-2 h-2 bg-purple-400 rounded-full animate-bounce"
                            style={{ animationDelay: '0.2s' }}
                          ></div>
                        </div>
                      )
                    )}
                  </div>
                </div>
              )}
            </motion.div>
          )}

          <div ref={messagesEndRef} />
        </div>
      </div>

      {/* Terminal Input */}
      <div className="border-t border-gray-800/50 p-4 sm:p-6">
        <div className="max-w-4xl mx-auto w-full">
          <TerminalInput
            onSendMessage={handleSendMessage}
            disabled={isLoading}
            companyId={companyId}
            onCompanyChange={onCompanyChange}
          />
        </div>
      </div>
    </div>
  )
}

