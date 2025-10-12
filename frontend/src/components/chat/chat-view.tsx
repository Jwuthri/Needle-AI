'use client'

import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles, Loader } from 'lucide-react'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'
import { TerminalInput } from './terminal-input'
import { EnhancedMessage } from './enhanced-message'
import { NeedleWelcome } from './needle-welcome'
import { EnhancedChatMessage } from '@/types/chat'
import { useChatStream } from '@/hooks/use-chat-stream'

interface ChatViewProps {
  companyId: string | null
  sessionId?: string
  onSessionIdChange?: (sessionId: string) => void
}

export function ChatView({ companyId, sessionId, onSessionIdChange }: ChatViewProps) {
  const { getToken } = useAuth()
  const [messages, setMessages] = useState<EnhancedChatMessage[]>([])
  const [isLoading, setIsLoading] = useState(false)
  const messagesEndRef = useRef<HTMLDivElement>(null)
  const isSendingRef = useRef(false)
  
  // Streaming chat hook
  const { 
    sendMessage: sendStreamMessage, 
    isStreaming, 
    currentContent, 
    currentTree, 
    status: streamStatus 
  } = useChatStream({
    onComplete: (response) => {
      // Add completed message to list
      const newMessage: EnhancedChatMessage = {
        id: response.message_id,
        content: response.message,
        role: 'assistant',
        timestamp: response.timestamp,
        metadata: response.metadata,
        execution_tree: response.execution_tree,
        visualization: response.visualization,
        sources: response.sources,
        output_format: response.output_format
      }
      setMessages(prev => [...prev, newMessage])
      setIsLoading(false)
    },
    onError: (error) => {
      console.error('Streaming error:', error)
      setIsLoading(false)
    }
  })

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
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="max-w-4xl mx-auto space-y-6">
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
                <EnhancedMessage 
                  key={message.id} 
                  message={message}
                  onQuestionClick={handleSendMessage}
                />
              ))}
            </div>
          )}

          {/* AI Response Area */}
          {(isLoading || isStreaming) && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="space-y-3"
            >
              <div className="flex items-start space-x-3">
                <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-green-600 rounded-full flex items-center justify-center flex-shrink-0">
                  <Sparkles className="w-4 h-4 text-white" />
                </div>
                <div className="flex-1">
                  {/* Status indicator or thinking state */}
                  {streamStatus ? (
                    <div className="text-xs text-emerald-400 mb-2 flex items-center space-x-2">
                      <Loader className="w-3 h-3 animate-spin" />
                      <span>{streamStatus.message}</span>
                    </div>
                  ) : !currentContent && (
                    <div className="text-xs text-emerald-400 mb-2 flex items-center space-x-2">
                      <Loader className="w-3 h-3 animate-spin" />
                      <span>Thinking...</span>
                    </div>
                  )}
                  
                  {/* Streaming content */}
                  {currentContent ? (
                    <div className="text-white/90 whitespace-pre-wrap">
                      {currentContent}
                      <span className="inline-block w-2 h-4 bg-emerald-400 ml-1 animate-pulse"></span>
                    </div>
                  ) : (
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
      <div className="border-t border-gray-800/50 p-6">
        <div className="max-w-4xl mx-auto">
          <TerminalInput
            onSendMessage={handleSendMessage}
            disabled={isLoading || !companyId}
            companyName={companyId ? 'company' : undefined}
          />
        </div>
      </div>
    </div>
  )
}

