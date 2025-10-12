'use client'

import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles } from 'lucide-react'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'
import { TerminalInput } from './terminal-input'
import { EnhancedMessage } from './enhanced-message'
import { NeedleWelcome } from './needle-welcome'
import { EnhancedChatMessage } from '@/types/chat'

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

  const scrollToBottom = () => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }

  useEffect(() => {
    scrollToBottom()
  }, [messages])

  // Load messages when session changes
  useEffect(() => {
    const loadSession = async () => {
      if (!sessionId) {
        setMessages([])
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

    setIsLoading(true)

    try {
      const token = await getToken()
      const api = createApiClient(token)

      // Create a new session if one doesn't exist
      let currentSessionId = sessionId
      if (!currentSessionId) {
        const newSession = await api.createSession()
        currentSessionId = newSession.session_id
        if (onSessionIdChange) {
          onSessionIdChange(currentSessionId)
        }
      }

      const response = await api.sendMessage({
        message,
        session_id: currentSessionId,
        company_id: companyId || undefined,
      })

      // Fetch updated session with all messages from database
      const updatedSession = await api.getSession(currentSessionId)
      
      // Convert to EnhancedChatMessage format
      const enhancedMessages: EnhancedChatMessage[] = updatedSession.messages.map((msg) => ({
        id: msg.id,
        content: msg.content,
        role: msg.role as 'user' | 'assistant' | 'system',
        timestamp: msg.timestamp,
        metadata: msg.metadata,
        query_type: response.query_type,
        pipeline_steps: response.pipeline_steps,
        sources: response.sources,
        related_questions: response.related_questions,
      }))
      
      setMessages(enhancedMessages)
      
      // Notify parent to refresh sessions list
      if (onSessionIdChange) {
        onSessionIdChange(currentSessionId)
      }
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
    } finally {
      setIsLoading(false)
    }
  }

  return (
    <div className="h-full flex flex-col">
      {/* Messages Area */}
      <div className="flex-1 overflow-y-auto px-6 py-6">
        <div className="max-w-4xl mx-auto space-y-6">
          {/* Welcome Message */}
          {messages.length === 0 && (
            <NeedleWelcome
              onPromptSelect={handleSendMessage}
              companySelected={!!companyId}
            />
          )}

          {/* Messages */}
          <AnimatePresence>
            {messages.map((message) => (
              <EnhancedMessage 
                key={message.id} 
                message={message}
                onQuestionClick={handleSendMessage}
              />
            ))}
          </AnimatePresence>

          {/* Loading indicator */}
          {isLoading && (
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="flex items-center space-x-3"
            >
              <div className="w-8 h-8 bg-gradient-to-br from-emerald-500 to-green-600 rounded-full flex items-center justify-center">
                <Sparkles className="w-4 h-4 text-white animate-pulse" />
              </div>
              <div className="text-white/60">
                <div className="flex space-x-1">
                  <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce"></div>
                  <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '0.1s' }}></div>
                  <div className="w-2 h-2 bg-emerald-400 rounded-full animate-bounce" style={{ animationDelay: '0.2s' }}></div>
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

