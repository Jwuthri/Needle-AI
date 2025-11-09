'use client'

import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, Loader, ChevronDown, ChevronUp, BarChart3, Zap, CheckCircle } from 'lucide-react'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'
import { TerminalInput } from './terminal-input'
import { EnhancedMessage } from './enhanced-message'
import { NeedleWelcome } from './needle-welcome'
import { EnhancedChatMessage, AgentStep } from '@/types/chat'
import { useChatStream } from '@/hooks/use-chat-stream'

// Simple markdown renderer for streaming content
function StreamingMarkdown({ content }: { content: string }) {
  const lines = content.split('\n')
  const elements: JSX.Element[] = []
  let currentTable: string[] = []
  let lineIndex = 0

  const renderTable = (tableLines: string[]) => {
    const filtered = tableLines.filter(l => !l.match(/^\s*\|[\s-:|]+\|\s*$/))
    if (filtered.length === 0) return null

    const headers = filtered[0].split('|').map(h => h.trim()).filter(h => h)
    const rows = filtered.slice(1).map(row => 
      row.split('|').map(c => c.trim()).filter(c => c)
    ).filter(row => row.length > 0)

    return (
      <div className="mb-4 overflow-x-auto">
        <table className="min-w-full border border-gray-700/30 rounded-lg overflow-hidden">
          <thead className="bg-gray-800/50">
            <tr>
              {headers.map((header, i) => (
                <th key={i} className="px-4 py-2 text-left text-xs font-semibold text-emerald-400 border-b border-gray-700/30">
                  {header}
                </th>
              ))}
            </tr>
          </thead>
          <tbody className="bg-gray-900/30">
            {rows.map((row, i) => (
              <tr key={i} className="border-b border-gray-700/20 hover:bg-gray-800/20">
                {row.map((cell, j) => (
                  <td key={j} className="px-4 py-2 text-sm text-white/80">
                    {cell}
                  </td>
                ))}
              </tr>
            ))}
          </tbody>
        </table>
      </div>
    )
  }

  for (let i = 0; i < lines.length; i++) {
    const line = lines[i]
    const trimmed = line.trim()

    // Table detection
    if (trimmed.startsWith('|') && trimmed.endsWith('|')) {
      currentTable.push(trimmed)
      continue
    }

    // Flush table if we have one
    if (currentTable.length > 0) {
      const table = renderTable(currentTable)
      if (table) elements.push(<div key={`table-${lineIndex++}`}>{table}</div>)
      currentTable = []
    }

    // Horizontal rule (----, ****, ____)
    if (/^(\-{3,}|\*{3,}|_{3,})$/.test(trimmed)) {
      elements.push(
        <hr key={lineIndex++} className="border-t border-gray-700/50 my-4" />
      )
      continue
    }

    // Headers (both # style and underline style)
    if (trimmed.startsWith('#')) {
      const match = trimmed.match(/^(#{1,6})\s+(.+)/)
      if (match) {
        const level = match[1].length
        const text = match[2]
        const className = level === 1 ? 'text-2xl' : level === 2 ? 'text-xl' : 'text-lg'
        elements.push(
          <h3 key={lineIndex++} className={`${className} font-semibold text-white mb-2 mt-2 flex items-center`}>
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full mr-2"></span>
            {text}
          </h3>
        )
        continue
      }
    }

    // Underline-style headers (check if next line is === or ---)
    if (i < lines.length - 1) {
      const nextLine = lines[i + 1].trim()
      if (trimmed && (/^={3,}$/.test(nextLine) || /^-{3,}$/.test(nextLine))) {
        const isH1 = /^={3,}$/.test(nextLine)
        const className = isH1 ? 'text-2xl' : 'text-xl'
        elements.push(
          <h3 key={lineIndex++} className={`${className} font-semibold text-white mb-2 mt-2 flex items-center`}>
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full mr-2"></span>
            {trimmed}
          </h3>
        )
        i++ // Skip the next line (the underline)
        continue
      }
    }

    // Bullet points
    if (trimmed.startsWith('-') || trimmed.startsWith('•') || trimmed.startsWith('*')) {
      // Check if it's a bullet (has text after) or just a horizontal rule handled above
      const bulletMatch = trimmed.match(/^[-•*]\s+(.+)/)
      if (bulletMatch) {
        elements.push(
          <div key={lineIndex++} className="flex items-start mb-2">
            <span className="text-emerald-400 mr-2">•</span>
            <span className="text-white/80">{bulletMatch[1]}</span>
          </div>
        )
        continue
      }
    }

    // Regular text
    if (trimmed) {
      elements.push(
        <p key={lineIndex++} className="text-white/80 mb-2">
          {line}
        </p>
      )
    } else {
      elements.push(<br key={lineIndex++} />)
    }
  }

  // Flush any remaining table
  if (currentTable.length > 0) {
    const table = renderTable(currentTable)
    if (table) elements.push(<div key={`table-${lineIndex++}`}>{table}</div>)
  }

  return <div className="space-y-1">{elements}</div>
}

// Helper function to format structured agent output - generic display of all fields
function formatAgentContent(content: any): JSX.Element | string {
  if (typeof content === 'string') {
    // No truncation - show full content
    return content
  }

  // Generic rendering of all fields in the structured output
  if (typeof content === 'object' && content !== null) {
    const entries = Object.entries(content)
    
    // Handle empty objects
    if (entries.length === 0) {
      return <span className="italic opacity-50">No data</span>
    }

    return (
      <div className="flex flex-col gap-1.5 font-mono">
        {entries.map(([key, value]) => {
          // Skip internal fields
          if (key.startsWith('_')) return null
          
          // Format the value
          let displayValue: string
          if (value === null || value === undefined) {
            displayValue = 'null'
          } else if (typeof value === 'boolean') {
            displayValue = value ? 'true' : 'false'
          } else if (typeof value === 'object') {
            // Handle arrays and nested objects - show full content
            displayValue = Array.isArray(value) 
              ? `[${value.length} items]`
              : JSON.stringify(value, null, 2)
          } else {
            displayValue = String(value)
          }

          // No truncation - show full content

          return (
            <div key={key} className="flex flex-col">
              <span className="text-emerald-400/80 text-xs">
                {key.replace(/_/g, ' ')}:
              </span>
              <span className="text-white/70 text-xs pl-2 whitespace-pre-wrap break-words">
                {displayValue}
              </span>
            </div>
          )
        })}
      </div>
    )
  }

  return <span className="flex items-center gap-1">
    <BarChart3 className="w-3 h-3" />
    Structured output
  </span>
}

interface ChatViewProps {
  companyId: string | null
  sessionId?: string
  onSessionIdChange?: (sessionId: string) => void
  onCompanyChange?: (companyId: string | null) => void
}

export function ChatView({ companyId, sessionId, onSessionIdChange, onCompanyChange }: ChatViewProps) {
  const { getToken } = useAuth()
  const [messages, setMessages] = useState<EnhancedChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const [expandedSteps, setExpandedSteps] = useState<Set<string>>(new Set())
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const isSendingRef = useRef(false)
  const lastCompletedMessageRef = useRef<string | null>(null)
  const currentAgentStepsRef = useRef<AgentStep[]>([])
  
  // Streaming chat hook
  const { 
    sendMessage: sendStreamMessage, 
    isStreaming, 
    currentContent,
    agentSteps,
    currentAgent,
    status: streamStatus 
  } = useChatStream({
    onComplete: (response) => {
      console.log('[ChatView] onComplete called with response:', response)
      console.log('[ChatView] currentAgentStepsRef.current:', currentAgentStepsRef.current.length)
      
      // Use the ref which contains the latest agent steps from streaming
      // Backend removes completed_steps from metadata before sending to frontend
      const formattedSteps = currentAgentStepsRef.current.map((step) => ({
        step_id: step.step_id,
        agent_name: step.agent_name,
        content: step.content,
        is_structured: step.is_structured,
        step_order: step.step_order,
        status: 'completed' as const,
        timestamp: step.timestamp
      }))
      
      console.log('[ChatView] Formatted steps from ref:', formattedSteps.length)
      
      const newMessage: EnhancedChatMessage = {
        id: response.message_id,
        content: response.message,
        role: 'assistant',
        timestamp: response.timestamp,
        metadata: response.metadata,
        agent_steps: formattedSteps,
        visualization: response.visualization,
        sources: response.sources,
        output_format: response.output_format
      }
      
      console.log('[ChatView] Adding message with agent_steps:', newMessage.agent_steps?.length || 0)
      
      // Mark this message as just completed to prevent reload overwriting it
      lastCompletedMessageRef.current = response.message_id
      
      setMessages(prev => [...prev, newMessage])
      setIsLoading(false)
      
      // Auto-expand execution steps for the new message
      if (formattedSteps.length > 0) {
        setExpandedSteps(prev => {
          const next = new Set(prev)
          next.add(response.message_id)
          return next
        })
      }
      
      // Clear the flag after 5 seconds to allow future reloads
      setTimeout(() => {
        if (lastCompletedMessageRef.current === response.message_id) {
          lastCompletedMessageRef.current = null
        }
      }, 5000)
    },
    onError: (error) => {
      console.error('Streaming error:', error)
      setIsLoading(false)
    }
  })

  // Keep ref in sync with agentSteps state to avoid closure issues
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
      
      // Don't reload if we're currently sending a message (to preserve local messages)
      if (isSendingRef.current) {
        console.log('Skipping session reload - currently sending message')
        return
      }
      
      // Don't reload if we just completed a message (to preserve agent_steps)
      if (lastCompletedMessageRef.current) {
        console.log('Skipping session reload - just completed message with agent steps')
        return
      }
      
      console.log('Loading session messages:', sessionId)
      
      try {
        const token = await getToken()
        const api = createApiClient(token)
        const session = await api.getSession(sessionId)
        
        const enhancedMessages: EnhancedChatMessage[] = session.messages.map((msg) => ({
          id: msg.id,
          content: msg.content,
          role: msg.role as 'user' | 'assistant' | 'system',
          timestamp: msg.timestamp,
          metadata: msg.metadata,
          agent_steps: msg.metadata?.agent_steps || [],
        }))
        
        setMessages(enhancedMessages)
      } catch (error) {
        console.error('Failed to load session:', error)
      }
    }
    
    loadSession()
  }, [sessionId, getToken])

  const handleSendMessage = async (message: string) => {
    if (!message.trim()) return

    // Set sending flag to prevent session reload
    isSendingRef.current = true
    // Clear agent steps ref for new message
    currentAgentStepsRef.current = []
    console.log('Starting message send, user message:', message)

    // Add user message immediately BEFORE setting loading state
    const userMessage: EnhancedChatMessage = {
      id: Date.now().toString(),
      content: message,
      role: 'user',
      timestamp: new Date().toISOString(),
    }
    setMessages(prev => {
      console.log('Adding user message to state')
      return [...prev, userMessage]
    })
    
    setIsLoading(true)

    try {
      const token = await getToken()
      const api = createApiClient(token)

      // Create a new session if one doesn't exist
      let currentSessionId = sessionId
      const isNewSession = !currentSessionId
      if (!currentSessionId) {
        const newSession = await api.createSession()
        currentSessionId = newSession.session_id
        console.log('Created new session:', currentSessionId)
        // Update parent session AFTER user message is added
        if (onSessionIdChange) {
          onSessionIdChange(currentSessionId)
        }
      }

      // Use streaming API to get real-time updates
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
      // Add error message
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
      // Clear sending flag after completion
      isSendingRef.current = false
      console.log('Message send complete')
    }
  }

  console.log('Rendering ChatView, messages count:', messages.length, 'isStreaming:', isStreaming, 'isLoading:', isLoading)
  
  return (
    <div className="h-full flex flex-col">
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
              {messages.map((message) => {
                console.log('[ChatView] Rendering message:', message.id, 'role:', message.role, 'agent_steps count:', message.agent_steps?.length || 0)
                return (
                <div key={message.id} className="space-y-3">
                  {/* Show execution steps above assistant messages */}
                  {message.role === 'assistant' && message.agent_steps && message.agent_steps.length > 0 && (() => {
                    // Calculate execution time from completed_at and created_at (timestamp)
                    let executionTimeSec = "0.00"
                    
                    if (message.completed_at && message.timestamp) {
                      const completedMs = new Date(message.completed_at).getTime()
                      const createdMs = new Date(message.timestamp).getTime()
                      const executionTimeMs = completedMs - createdMs
                      executionTimeSec = (executionTimeMs / 1000).toFixed(2)
                    }
                    
                    return (
                    <div className="bg-gradient-to-br from-purple-900/30 via-gray-900/50 to-blue-900/30 border border-purple-500/40 rounded-xl overflow-hidden shadow-lg shadow-purple-500/10">
                      <button
                        onClick={() => {
                          setExpandedSteps(prev => {
                            const next = new Set(prev)
                            if (next.has(message.id)) {
                              next.delete(message.id)
                            } else {
                              next.add(message.id)
                            }
                            return next
                          })
                        }}
                        className="w-full bg-gradient-to-r from-purple-500/10 via-purple-500/5 to-blue-500/10 px-5 py-4 border-b border-purple-500/20 hover:from-purple-500/20 hover:to-blue-500/20 transition-all duration-300"
                      >
                        <div className="flex items-center justify-between">
                          <div className="flex items-center space-x-3">
                            <div className="relative">
                              <div className="w-8 h-8 rounded-lg bg-gradient-to-br from-purple-500/30 to-blue-500/30 flex items-center justify-center border border-purple-400/40 shadow-lg shadow-purple-500/20">
                                <span className="text-sm font-bold text-purple-300">{message.agent_steps.length}</span>
                              </div>
                              <div className="absolute -inset-1 bg-gradient-to-r from-purple-500 to-blue-500 rounded-lg opacity-20 blur"></div>
                            </div>
                            <div className="text-left">
                              <div className="flex items-center space-x-2">
                                <span className="text-white font-semibold">Execution Pipeline</span>
                                <Zap className="w-4 h-4 text-yellow-400" />
                              </div>
                            </div>
                          </div>
                          <div className="flex items-center space-x-2">
                            <span className="text-xs text-purple-300/70 font-mono">{message.agent_steps.length} steps</span>
                            {expandedSteps.has(message.id) ? (
                              <ChevronUp className="w-5 h-5 text-white/60" />
                            ) : (
                              <ChevronDown className="w-5 h-5 text-white/60" />
                            )}
                          </div>
                        </div>
                      </button>
                      
                      {expandedSteps.has(message.id) && (
                        <div className="p-5 space-y-3 relative">
                          {/* Timeline connector line */}
                          <div className="absolute left-9 top-5 bottom-5 w-0.5 bg-gradient-to-b from-purple-500/30 via-blue-500/30 to-emerald-500/30"></div>
                          
                          {message.agent_steps.map((step, index) => {
                            const isLast = index === message.agent_steps.length - 1
                            return (
                            <div
                              key={step.step_id}
                              className="relative bg-gray-800/40 backdrop-blur-sm border border-gray-700/40 rounded-xl overflow-hidden hover:border-purple-500/30 transition-all duration-300"
                            >
                              {/* Timeline dot */}
                              <div className="absolute left-[-38px] top-5 w-3 h-3 rounded-full bg-gradient-to-br from-purple-500 to-blue-500 ring-4 ring-gray-900/50 shadow-lg shadow-purple-500/50"></div>
                              
                              {/* Step Header */}
                              <div className="p-4 bg-gradient-to-r from-gray-800/60 to-gray-800/40">
                                <div className="flex items-start justify-between">
                                  <div className="flex items-center space-x-3">
                                    {/* Step Number Badge */}
                                    <div className="flex-shrink-0 w-9 h-9 rounded-lg bg-gradient-to-br from-purple-500/20 to-blue-500/20 text-purple-300 flex items-center justify-center font-bold text-sm border border-purple-500/40 shadow-md">
                                      {(step.step_order ?? index) + 1}
                                    </div>
                                    <div>
                                      <div className="flex items-center space-x-2">
                                        <span className="text-white text-sm font-semibold font-mono bg-gradient-to-r from-purple-400 to-blue-400 bg-clip-text text-transparent">
                                          {step.agent_name}
                                        </span>
                                        {step.is_structured && (
                                          <span className="text-xs bg-gradient-to-r from-blue-500/20 to-cyan-500/20 text-blue-300 px-2 py-1 rounded-md border border-blue-500/40 flex items-center gap-1 shadow-sm">
                                            <BarChart3 className="w-3 h-3" />
                                            Structured
                                          </span>
                                        )}
                                        {isLast && (
                                          <span className="text-xs bg-gradient-to-r from-emerald-500/20 to-green-500/20 text-emerald-300 px-2 py-1 rounded-md border border-emerald-500/40 flex items-center gap-1">
                                            <CheckCircle className="w-3 h-3" />
                                            Final
                                          </span>
                                        )}
                                      </div>
                                      {step.timestamp && (
                                        <div className="text-xs text-white/40 mt-1.5 font-mono">
                                          {new Date(step.timestamp).toLocaleTimeString()}
                                        </div>
                                      )}
                                    </div>
                                  </div>
                                  <button
                                    onClick={(e) => {
                                      e.stopPropagation()
                                      navigator.clipboard.writeText(
                                        step.is_structured ? JSON.stringify(step.content, null, 2) : step.content
                                      )
                                    }}
                                    className="p-2 text-white/40 hover:text-white transition-colors rounded-lg hover:bg-white/10"
                                    title="Copy to clipboard"
                                  >
                                    <svg className="w-4 h-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M8 16H6a2 2 0 01-2-2V6a2 2 0 012-2h8a2 2 0 012 2v2m-6 12h8a2 2 0 002-2v-8a2 2 0 00-2-2h-8a2 2 0 00-2 2v8a2 2 0 002 2z" />
                                    </svg>
                                  </button>
                                </div>
                              </div>

                              {/* Step Content */}
                              <div className="p-4 bg-gray-900/40 max-h-[400px] overflow-y-auto scrollbar-thin scrollbar-thumb-purple-500/30 scrollbar-track-gray-800/50">
                                {step.is_structured ? (
                                  <div className="text-xs text-white/70">
                                    {formatAgentContent(step.content)}
                                  </div>
                                ) : (
                                  <div className="text-sm text-white/80 whitespace-pre-wrap leading-relaxed">
                                    {step.content}
                                  </div>
                                )}
                              </div>
                            </div>
                          )})}
                        </div>
                      )}
                    </div>
                    )
                  })()}
                  
                  {/* Message */}
                  <EnhancedMessage 
                    message={message}
                    onQuestionClick={handleSendMessage}
                  />
                </div>
                )
              })}
            </div>
          )}

          {/* AI Response Area */}
          {(isLoading || isStreaming) && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-3"
            >
              {/* Agent Execution Pipeline - Purple Box Style */}
              {agentSteps.length > 0 && (
                <div className="bg-gray-900/50 border border-purple-500/30 rounded-xl overflow-hidden">
                  <div className="bg-purple-500/10 px-4 py-3 border-b border-purple-500/20">
                    <div className="flex items-center space-x-2">
                      <div className="w-6 h-6 rounded-lg bg-purple-500/20 flex items-center justify-center border border-purple-500/30">
                        <Loader className="w-3 h-3 animate-spin text-purple-400" />
                      </div>
                      <span className="text-white font-medium">Agent Execution Pipeline</span>
                    </div>
                  </div>
                  
                  <div className="p-4 space-y-2">
                    {agentSteps.map((step) => (
                      <div
                        key={step.step_id}
                        className={`p-3 rounded-lg transition-all ${
                          step.status === 'active' 
                            ? 'bg-emerald-500/10 border border-emerald-500/30' 
                            : 'bg-gray-800/30 border border-gray-700/30'
                        }`}
                      >
                        <div className="flex items-start space-x-3">
                          {/* Step Number Badge */}
                          <div className={`flex-shrink-0 w-8 h-8 rounded-full flex items-center justify-center text-sm font-bold transition-all ${
                            step.status === 'active' 
                              ? 'bg-emerald-500/20 text-emerald-400 ring-2 ring-emerald-500/50 shadow-lg shadow-emerald-500/20' 
                              : 'bg-purple-500/20 text-purple-400 border border-purple-500/30'
                          }`}>
                            {(step.step_order ?? 0) + 1}
                          </div>
                          
                          {/* Status Icon */}
                          {step.status === 'active' ? (
                            <Loader className="w-4 h-4 animate-spin flex-shrink-0 text-emerald-400 mt-1" />
                          ) : (
                            <span className="w-4 h-4 flex items-center justify-center flex-shrink-0 text-green-500 text-base mt-1">✓</span>
                          )}
                          
                          {/* Agent Info */}
                          <div className="flex-1 min-w-0">
                            <div className="flex items-center space-x-2 mb-1">
                              <span className={`text-sm font-mono font-semibold ${
                                step.status === 'active' ? 'text-emerald-400' : 'text-white/70'
                              }`}>
                                {step.agent_name}
                              </span>
                              <span className={`text-xs flex items-center gap-1 ${
                                step.status === 'active' ? 'text-emerald-400/80' : 'text-gray-500'
                              }`}>
                                {step.status === 'active' ? (
                                  <>
                                    <Zap className="w-3 h-3" />
                                    Running...
                                  </>
                                ) : (
                                  <>
                                    <CheckCircle className="w-3 h-3" />
                                    Completed
                                  </>
                                )}
                              </span>
                            </div>
                            
                            {/* Show content preview if available */}
                            {step.content && (
                              <div className={`mt-2 text-xs ${
                                step.status === 'active' ? 'text-emerald-300/60' : 'text-gray-400/80'
                              }`}>
                                {formatAgentContent(step.content)}
                              </div>
                            )}
                          </div>
                        </div>
                      </div>
                    ))}
                  </div>
                </div>
              )}

              {/* AI Response with streaming content */}
              <div className="flex items-start space-x-3">
                <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-green-600 rounded-full flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
                <div className="flex-1">
                  {/* Status indicator when no agents yet */}
                  {streamStatus && !agentSteps.length && (
                    <div className="text-xs text-emerald-400 mb-2 flex items-center space-x-2">
                      <Loader className="w-3 h-3 animate-spin" />
                      <span>{streamStatus.message}</span>
                    </div>
                  )}
                  
                  {/* Streaming content */}
                  {currentContent ? (
                    <div className="text-white/90">
                      <StreamingMarkdown content={currentContent} />
                      <span className="inline-block w-2 h-4 bg-emerald-400 ml-1 animate-pulse"></span>
                    </div>
                  ) : !agentSteps.length && (
                    <div className="flex space-x-1">
                      <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce"></div>
                      <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                      <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
                    </div>
                  )}
                </div>
              </div>
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

