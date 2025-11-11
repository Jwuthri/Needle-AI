'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { User, Sparkles, ChevronDown, ChevronUp, ExternalLink, Copy, ThumbsUp, ThumbsDown } from 'lucide-react'
import { EnhancedChatMessage } from '@/types/chat'
import ReactMarkdown from 'react-markdown'
import { VisualizationRenderer } from './visualization-renderer'
import { SourceCitations } from './source-citations'

interface MessageWithSourcesProps {
  message: EnhancedChatMessage
}

export function MessageWithSources({ message }: MessageWithSourcesProps) {
  const [showSources, setShowSources] = useState(false)
  const [showRelatedQuestions, setShowRelatedQuestions] = useState(false)

  const isUser = message.role === 'user'

  const getSentimentColor = (sentiment: number) => {
    if (sentiment > 0.5) return 'text-green-400'
    if (sentiment < -0.5) return 'text-red-400'
    return 'text-yellow-400'
  }

  const getSentimentLabel = (sentiment: number) => {
    if (sentiment > 0.5) return 'Positive'
    if (sentiment < -0.5) return 'Negative'
    return 'Neutral'
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex ${isUser ? 'justify-end' : 'justify-start'}`}
    >
      <div className={`flex items-start space-x-3 max-w-[85%] ${isUser ? 'flex-row-reverse space-x-reverse' : ''}`}>
        {/* Avatar */}
        <div className={`w-8 h-8 rounded-full flex items-center justify-center flex-shrink-0 ${
          isUser ? 'bg-blue-500/20 text-blue-400' : 'bg-emerald-500/20 text-emerald-400'
        }`}>
          {isUser ? <User className="w-5 h-5" /> : <Sparkles className="w-5 h-5" />}
        </div>

        {/* Message Content */}
        <div className="flex-1">
          <div className={`rounded-xl p-4 ${
            isUser 
              ? 'bg-blue-500/10 border border-blue-500/30' 
              : message.error
              ? 'bg-red-500/10 border border-red-500/30'
              : 'bg-gray-800/50 border border-gray-700/50'
          }`}>
            <div className="prose prose-invert max-w-none">
              <ReactMarkdown className="text-white">
                {message.content}
              </ReactMarkdown>
            </div>

            {/* Query Type Badge */}
            {message.query_type && (
              <div className="mt-3 inline-flex items-center px-2 py-1 bg-emerald-500/10 border border-emerald-500/30 rounded text-emerald-400 text-xs">
                {message.query_type.replace('_', ' ')}
              </div>
            )}
          </div>

          {/* Visualization */}
          {!isUser && message.visualization && (
            <div className="mt-4">
              <VisualizationRenderer config={message.visualization} />
            </div>
          )}

          {/* Source Citations */}
          {!isUser && message.sources && message.sources.length > 0 && (
            <div className="mt-4">
              <SourceCitations 
                sources={message.sources.map((source: any, idx: number) => ({
                  id: source.review_id || `source-${idx}`,
                  index: idx + 1,
                  author: source.author || 'Anonymous',
                  source: source.source || 'Unknown',
                  url: source.url,
                  date: source.date,
                  sentiment: getSentimentLabel(source.sentiment),
                  relevance_score: source.relevance_score,
                  quote: source.content?.substring(0, 150) + '...',
                  full_content: source.content,
                }))}
              />
            </div>
          )}

          {/* Related Questions */}
          {!isUser && message.related_questions && message.related_questions.length > 0 && (
            <div className="mt-4">
              <div className="border border-gray-200 rounded-lg bg-white p-4">
                <button
                  onClick={() => setShowRelatedQuestions(!showRelatedQuestions)}
                  className="flex items-center space-x-2 text-gray-700 hover:text-gray-900 transition-colors text-sm font-medium"
                >
                  <span>Related questions</span>
                  {showRelatedQuestions ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>

                {showRelatedQuestions && (
                  <div className="mt-3 space-y-2">
                    {message.related_questions.map((question, idx) => (
                      <button
                        key={idx}
                        className="w-full text-left p-2 text-sm text-gray-600 hover:text-blue-600 hover:bg-gray-50 rounded transition-colors"
                      >
                        → {question}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            </div>
          )}

          {/* Message Actions */}
          {!isUser && !message.error && (
            <div className="flex items-center space-x-2 mt-2">
              <button className="p-1 text-white/40 hover:text-emerald-400 transition-colors">
                <ThumbsUp className="w-4 h-4" />
              </button>
              <button className="p-1 text-white/40 hover:text-red-400 transition-colors">
                <ThumbsDown className="w-4 h-4" />
              </button>
              <button
                onClick={() => navigator.clipboard.writeText(message.content)}
                className="p-1 text-white/40 hover:text-white transition-colors"
              >
                <Copy className="w-4 h-4" />
              </button>
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}

