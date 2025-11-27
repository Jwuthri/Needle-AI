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
import { MarkdownRenderer } from './markdown-renderer'
import { WorkflowSteps } from './workflow-steps'
import { UserDataset } from '@/types/user-dataset'

interface ExperimentalChatViewProps {
  companyId: string | null
  sessionId?: string
  onSessionIdChange?: (sessionId: string) => void
  onCompanyChange?: (companyId: string | null) => void
  datasetId?: string | null
  onDatasetChange?: (datasetId: string | null) => void
}

export function ExperimentalChatView({
  companyId,
  sessionId,
  onSessionIdChange,
  onCompanyChange,
  datasetId,
  onDatasetChange
}: ExperimentalChatViewProps) {
  const { getToken } = useAuth()
  const [messages, setMessages] = useState<EnhancedChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set())
  const [streamingStepsExpanded, setStreamingStepsExpanded] = useState(true)
  const [datasets, setDatasets] = useState<UserDataset[]>([])
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const currentAgentStepsRef = useRef<any[]>([])
  const isSendingRef = useRef(false)
  const sessionIdRef = useRef<string | undefined>(sessionId)

  // Load datasets
  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        const token = await getToken()
        const api = createApiClient(token)
        const datasetsData = await api.listUserDatasets()
        setDatasets(datasetsData.datasets || [])
      } catch (error) {
        console.error('Failed to fetch datasets:', error)
      }
    }

    fetchDatasets()
  }, [getToken])

  // Use experimental streaming hook
  const {
    sendMessage: sendStreamMessage,
    isStreaming,
    currentContent,
    agentSteps,
    currentAgent,
    status: streamStatus,
    toolExecutions,
    thinkingText,
    activeToolCalls,
  } = useExperimentalChatStream({
    onComplete: (response) => {
      // Use steps from the hook (already tracked during streaming)
      // Filter out empty steps and format them
      const formattedSteps = currentAgentStepsRef.current
        .filter(step => {
          // Keep structured steps (tool calls)
          if (step.is_structured && step.content) return true
          // Keep text steps with actual content
          if (step.content && typeof step.content === 'string' && step.content.trim()) return true
          return false
        })
        .map((step, index) => ({
          step_id: step.step_id || `step-${index}`,
          agent_name: step.agent_name,
          content: step.content,
          is_structured: step.is_structured || false,
          step_order: step.step_order ?? index,
          status: 'completed' as const,
          timestamp: step.timestamp,
          raw_output: step.raw_output,
        }))

      const newMessage: EnhancedChatMessage = {
        id: response.message_id || Date.now().toString(),
        content: response.message || response.content || '',
        role: 'assistant',
        timestamp: response.timestamp || new Date().toISOString(),
        completed_at: response.completed_at,
        metadata: response.metadata,
        agent_steps: formattedSteps,
      }

      setMessages((prev) => [...prev, newMessage])
      setIsLoading(false)
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
        // Don't clear messages if we're currently sending (session is being created)
        if (isSendingRef.current || isLoading || isStreaming) {
          return
        }
        setMessages([])
        return
      }

      // Don't reload session while sending/streaming to prevent clearing current messages
      // UNLESS the sessionId actually changed (user switched tabs)
      const sessionChanged = sessionIdRef.current !== sessionId

      if (!sessionChanged && (isStreaming || isLoading || isSendingRef.current)) {
        return
      }

      // Update session ref
      sessionIdRef.current = sessionId

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
    
    // Ensure workflow execution starts expanded for new stream
    setStreamingStepsExpanded(true)

    // Add user message immediately so it's visible during streaming
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
        // Update the ref BEFORE calling onSessionIdChange to prevent reload
        sessionIdRef.current = currentSessionId
        if (onSessionIdChange) {
          onSessionIdChange(currentSessionId)
        }
      }

      // Use experimental streaming
      const selectedDataset = datasetId ? datasets.find(d => d.id === datasetId) : undefined
      
      await sendStreamMessage(
        {
          message,
          session_id: currentSessionId,
          company_id: companyId || undefined,
          dataset_id: datasetId || undefined,
          dataset_table_name: selectedDataset?.table_name,
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
        agent_steps: []
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

          {/* Messages - ALWAYS show if there are messages, even during loading */}
          {messages.length > 0 ? (
            <div className="space-y-6">
              {messages.map((message) => {
                // Filter out REPORTER steps for workflow display (count only non-REPORTER)
                const workflowSteps = message.agent_steps?.filter(
                  s => s.agent_name?.toUpperCase() !== 'REPORTER'
                ) || []
                
                return (
                  <div key={message.id} className="space-y-3">
                    {/* Show execution steps above assistant messages - WorkflowSteps filters REPORTER */}
                    {message.role === 'assistant' && workflowSteps.length > 0 && (
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
                                  {workflowSteps.length}
                                </span>
                              </div>
                              <span className="text-white font-semibold">
                                Workflow Execution
                              </span>
                            </div>
                            <div className="flex items-center space-x-2">
                              <span className="text-xs text-purple-300/70 font-mono">
                                {workflowSteps.length} steps
                              </span>
                              {expandedSteps.has(message.id) ? (
                                <ChevronUp className="w-5 h-5 text-white/60" />
                              ) : (
                                <ChevronDown className="w-5 h-5 text-white/60" />
                              )}
                            </div>
                          </div>
                        </button>

                        {/* WorkflowSteps filters out REPORTER internally */}
                        <WorkflowSteps 
                          steps={message.agent_steps as any[]} 
                          expanded={expandedSteps.has(message.id)} 
                        />
                      </div>
                    )}

                    {/* Message */}
                    <EnhancedMessage message={message} onQuestionClick={handleSendMessage} />
                  </div>
                )
              })}
            </div>
          ) : null}

          {/* AI Response Area - Streaming */}
          {(isLoading || isStreaming) && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-3"
            >
              {/* Workflow Pipeline - Show whenever we have non-REPORTER steps */}
              {(() => {
                // Filter out REPORTER for display count (it shows in answer area)
                const workflowSteps = agentSteps.filter(s => s.agent_name?.toUpperCase() !== 'REPORTER')
                if (workflowSteps.length === 0) return null
                
                const completedCount = workflowSteps.filter(s => s.status === 'completed').length
                
                return (
                  <div className="bg-gradient-to-br from-purple-900/30 via-gray-900/50 to-blue-900/30 border border-purple-500/40 rounded-xl overflow-hidden">
                    <button
                      onClick={() => setStreamingStepsExpanded(!streamingStepsExpanded)}
                      className="w-full px-6 py-4 flex items-center justify-between hover:bg-white/5 transition-colors"
                    >
                      <div className="flex items-center space-x-3">
                        <div className="w-8 h-8 bg-purple-500/20 rounded-lg flex items-center justify-center">
                          <Zap className="w-4 h-4 text-purple-400" />
                        </div>
                        <div className="text-left">
                          <div className="text-sm font-medium text-white">Workflow Execution</div>
                          <div className="text-xs text-gray-400">
                            {completedCount} / {workflowSteps.length} steps completed
                          </div>
                        </div>
                      </div>
                      <div className="flex items-center space-x-2">
                        {streamingStepsExpanded ? (
                          <ChevronUp className="w-4 h-4 text-gray-400" />
                        ) : (
                          <ChevronDown className="w-4 h-4 text-gray-400" />
                        )}
                      </div>
                    </button>

                    {/* WorkflowSteps filters out REPORTER internally */}
                    <WorkflowSteps 
                      steps={agentSteps as any[]} 
                      currentContent={currentContent}
                      expanded={streamingStepsExpanded} 
                    />
                  </div>
                )
              })()}

              {/* Thinking text streaming */}
              {thinkingText && (
                <div className="bg-purple-900/20 border border-purple-500/30 rounded-lg p-3">
                  <div className="flex items-center space-x-2 mb-2">
                    <Loader className="w-3 h-3 animate-spin text-purple-400" />
                    <span className="text-xs text-purple-300 font-semibold">Thinking...</span>
                  </div>
                  <div className="text-sm text-purple-200/80 font-mono whitespace-pre-wrap">
                    {thinkingText}
                    <span className="inline-block w-2 h-4 bg-purple-400 ml-1 animate-pulse"></span>
                  </div>
                </div>
              )}

              {/* Active tool calls streaming */}
              {activeToolCalls.length > 0 && (
                <div className="space-y-2">
                  {activeToolCalls.map((toolCall) => (
                    <div
                      key={toolCall.tool_id}
                      className="bg-blue-900/20 border border-blue-500/30 rounded-lg p-3"
                    >
                      <div className="flex items-center space-x-2 mb-2">
                        <Loader className="w-3 h-3 animate-spin text-blue-400" />
                        <span className="text-xs text-blue-300 font-semibold font-mono">
                          {toolCall.tool_name}(
                        </span>
                      </div>
                      <div className="pl-5 space-y-1">
                        {Object.entries(toolCall.params).map(([key, value]) => (
                          <div key={key} className="text-xs font-mono">
                            <span className="text-blue-400">{key}</span>
                            <span className="text-white/60">=</span>
                            <span className="text-emerald-300">
                              {value === null ? (
                                <span className="text-gray-400 italic">...</span>
                              ) : (
                                JSON.stringify(value)
                              )}
                            </span>
                          </div>
                        ))}
                        <div className="text-xs text-blue-300 font-mono">
                          )
                          <span className="inline-block w-2 h-3 bg-blue-400 ml-1 animate-pulse"></span>
                        </div>
                      </div>
                    </div>
                  ))}
                </div>
              )}

              {/* AI Response with streaming content - Show REPORTER content in answer box */}
              {(() => {
                // Show content in answer box when REPORTER is active
                const currentAgentIsReporter = currentAgent?.toUpperCase() === 'REPORTER'
                
                // Find REPORTER step if it exists and has text content
                const reporterStep = agentSteps.find(s => 
                  s.agent_name?.toUpperCase() === 'REPORTER' && 
                  typeof s.content === 'string' && 
                  s.content.trim()
                )
                
                // Show Reporter content: use currentContent when Reporter is active, otherwise use saved step content
                const contentToShow = currentAgentIsReporter 
                  ? currentContent 
                  : (reporterStep?.content as string || '')
                
                if (contentToShow) {
                  return (
                    <div className="bg-gray-800/50 border border-gray-700/50 rounded-2xl p-6 max-h-[1000px] overflow-auto w-full">
                      <div className="flex items-start space-x-3">
                        <div className="w-8 h-8 bg-gradient-to-br from-purple-500 to-blue-600 rounded-full flex items-center justify-center flex-shrink-0">
                          <Sparkles className="w-4 h-4 text-white" />
                        </div>
                        <div className="flex-1 min-w-0 max-w-full overflow-hidden">
                          <div className="text-white/90">
                            <MarkdownRenderer content={contentToShow} />
                            {currentAgentIsReporter && isStreaming && (
                              <span className="inline-block w-2 h-4 bg-purple-400 ml-1 animate-pulse"></span>
                            )}
                          </div>
                        </div>
                      </div>
                    </div>
                  )
                }
                return null
              })()}

              {/* Fallback status indicator when no content yet */}
              {isStreaming && !currentContent && agentSteps.length === 0 && (
                <div className="flex items-center space-x-3 px-4 py-3 bg-purple-500/10 border border-purple-500/20 rounded-lg">
                  <Loader className="w-4 h-4 animate-spin text-purple-400" />
                  <div className="flex-1">
                    <div className="text-sm text-purple-300 font-medium">Thinking...</div>
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
            datasetId={datasetId}
            onDatasetChange={onDatasetChange}
          />
        </div>
      </div>
    </div>
  )
}
