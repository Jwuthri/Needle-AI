'use client'

import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'
import { PipelineVisualizer } from './pipeline-visualizer'
import { EnhancedChatMessage } from '@/types/chat'

interface TreeViewProps {
  companyId: string | null
  sessionId?: string
}

export function TreeView({ companyId, sessionId }: TreeViewProps) {
  const { getToken } = useAuth()
  const [messages, setMessages] = useState<EnhancedChatMessage[]>([])
  const [selectedMessage, setSelectedMessage] = useState<EnhancedChatMessage | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    const fetchMessages = async () => {
      if (!sessionId) return

      setLoading(true)
      try {
        const token = await getToken()
        const api = createApiClient(token)
        const session = await api.getSession(sessionId)
        setMessages(session.messages || [])
        
        // Select the last assistant message by default
        const lastAssistantMessage = session.messages?.reverse().find((m: any) => m.role === 'assistant')
        if (lastAssistantMessage) {
          setSelectedMessage(lastAssistantMessage)
        }
      } catch (error) {
        console.error('Failed to fetch messages:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchMessages()
  }, [sessionId, getToken])

  if (!sessionId || !companyId) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">🌳</div>
          <div className="text-white text-xl font-semibold mb-2">No Session Selected</div>
          <div className="text-white/60">
            Start a chat session to see the pipeline visualization
          </div>
        </div>
      </div>
    )
  }

  if (loading) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-emerald-400 text-lg">Loading pipeline...</div>
      </div>
    )
  }

  const assistantMessages = messages.filter((m) => m.role === 'assistant' && m.pipeline_steps)

  if (assistantMessages.length === 0) {
    return (
      <div className="h-full flex items-center justify-center">
        <div className="text-center">
          <div className="text-6xl mb-4">🌳</div>
          <div className="text-white text-xl font-semibold mb-2">No Pipeline Data</div>
          <div className="text-white/60">
            Send a message to see how the AI processes your query
          </div>
        </div>
      </div>
    )
  }

  return (
    <div className="h-full flex">
      {/* Message List Sidebar */}
      <div className="w-80 border-r border-gray-800/50 bg-gray-900/30 overflow-y-auto">
        <div className="p-4 border-b border-gray-800/50">
          <h3 className="text-white font-semibold">Query History</h3>
          <p className="text-white/40 text-sm mt-1">Select a message to view pipeline</p>
        </div>
        <div className="p-2 space-y-2">
          {assistantMessages.map((message, idx) => {
            // Find the corresponding user message
            const messageIndex = messages.findIndex((m) => m.id === message.id)
            const userMessage = messageIndex > 0 ? messages[messageIndex - 1] : null

            return (
              <button
                key={message.id}
                onClick={() => setSelectedMessage(message)}
                className={`w-full text-left p-3 rounded-lg transition-all ${
                  selectedMessage?.id === message.id
                    ? 'bg-emerald-500/10 border border-emerald-500/30'
                    : 'bg-gray-800/50 border border-gray-700/50 hover:border-emerald-500/30'
                }`}
              >
                <div className="text-white/80 text-sm font-medium mb-1 line-clamp-2">
                  {userMessage?.content || `Query ${idx + 1}`}
                </div>
                <div className="text-white/40 text-xs">
                  {message.pipeline_steps?.length || 0} steps • {new Date(message.timestamp).toLocaleTimeString()}
                </div>
              </button>
            )
          })}
        </div>
      </div>

      {/* Pipeline Visualization */}
      <div className="flex-1 overflow-auto p-8">
        {selectedMessage && selectedMessage.pipeline_steps ? (
          <PipelineVisualizer steps={selectedMessage.pipeline_steps} message={selectedMessage} />
        ) : (
          <div className="h-full flex items-center justify-center text-white/40">
            Select a message to view its pipeline
          </div>
        )}
      </div>
    </div>
  )
}

