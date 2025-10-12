'use client'

import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Sparkles } from 'lucide-react'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'
import { TerminalInput } from './terminal-input'
import { MessageWithSources } from './message-with-sources'
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

  const handleSendMessage = async (message: string) => {
    if (!message.trim()) return

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

      const response = await api.sendMessage({
        message,
        session_id: sessionId,
        company_id: companyId || undefined,
      })

      // Update session ID if this is a new session
      if (!sessionId && response.session_id && onSessionIdChange) {
        onSessionIdChange(response.session_id)
      }

      // Add assistant message
      const assistantMessage: EnhancedChatMessage = {
        id: response.message_id,
        content: response.message,
        role: 'assistant',
        timestamp: response.timestamp,
        query_type: response.query_type,
        pipeline_steps: response.pipeline_steps,
        sources: response.sources,
        related_questions: response.related_questions,
      }

      setMessages((prev) => [...prev, assistantMessage])
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
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="text-center py-12"
            >
              <div className="w-20 h-20 bg-gradient-to-br from-emerald-500 to-green-600 rounded-full flex items-center justify-center mx-auto mb-6">
                <Sparkles className="w-10 h-10 text-white" />
              </div>
              <h2 className="text-2xl font-bold text-white mb-4">
                {companyId ? 'Ready to Analyze' : 'Select a Company'}
              </h2>
              <p className="text-white/70 mb-8 max-w-md mx-auto">
                {companyId
                  ? 'Ask questions about reviews, discover insights, or explore customer sentiment.'
                  : 'Please select a company from the dropdown above to start chatting.'}
              </p>

              {/* Example prompts */}
              {companyId && (
                <div className="grid md:grid-cols-2 gap-4 max-w-2xl mx-auto">
                  {[
                    { emoji: '🔍', title: 'Product Gaps', prompt: 'What are the main product gaps mentioned in reviews?' },
                    { emoji: '😊', title: 'Sentiment', prompt: 'What is the overall sentiment of our reviews?' },
                    { emoji: '🏆', title: 'Competitors', prompt: 'Which competitors are mentioned most often?' },
                    { emoji: '💡', title: 'Features', prompt: 'What features are customers requesting?' },
                  ].map((example) => (
                    <motion.button
                      key={example.prompt}
                      whileHover={{ scale: 1.02 }}
                      whileTap={{ scale: 0.98 }}
                      onClick={() => handleSendMessage(example.prompt)}
                      className="p-4 bg-gray-800/50 border border-gray-700/50 rounded-lg text-left hover:border-emerald-500/50 transition-all group"
                    >
                      <div className="text-white font-medium mb-2">{example.emoji} {example.title}</div>
                      <div className="text-white/60 text-sm group-hover:text-white/80 transition-colors">
                        {example.prompt}
                      </div>
                    </motion.button>
                  ))}
                </div>
              )}
            </motion.div>
          )}

          {/* Messages */}
          <AnimatePresence>
            {messages.map((message) => (
              <MessageWithSources key={message.id} message={message} />
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

