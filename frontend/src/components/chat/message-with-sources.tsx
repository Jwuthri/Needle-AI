'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { User, Sparkles, ChevronDown, ChevronUp, ExternalLink, Copy, ThumbsUp, ThumbsDown } from 'lucide-react'
import { EnhancedChatMessage } from '@/types/chat'
import ReactMarkdown from 'react-markdown'

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

            {/* Sources */}
            {message.sources && message.sources.length > 0 && (
              <div className="mt-4 pt-4 border-t border-gray-700/50">
                <button
                  onClick={() => setShowSources(!showSources)}
                  className="flex items-center space-x-2 text-emerald-400 hover:text-emerald-300 transition-colors text-sm"
                >
                  <span className="font-medium">{message.sources.length} sources</span>
                  {showSources ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>

                {showSources && (
                  <div className="mt-3 space-y-2">
                    {message.sources.map((source) => (
                      <div
                        key={source.review_id}
                        className="p-3 bg-gray-900/50 border border-gray-700/30 rounded-lg"
                      >
                        <div className="flex items-start justify-between mb-2">
                          <div className="flex items-center space-x-2">
                            <span className="text-white/80 text-sm font-medium">{source.author}</span>
                            <span className="text-white/40 text-xs">•</span>
                            <span className="text-white/40 text-xs">{source.source}</span>
                            <span className={`text-xs font-medium ${getSentimentColor(source.sentiment)}`}>
                              {getSentimentLabel(source.sentiment)}
                            </span>
                          </div>
                          {source.url && (
                            <a
                              href={source.url}
                              target="_blank"
                              rel="noopener noreferrer"
                              className="text-emerald-400 hover:text-emerald-300"
                            >
                              <ExternalLink className="w-4 h-4" />
                            </a>
                          )}
                        </div>
                        <p className="text-white/60 text-sm line-clamp-3">{source.content}</p>
                        <div className="mt-2 text-xs text-white/40">
                          Relevance: {(source.relevance_score * 100).toFixed(0)}%
                        </div>
                      </div>
                    ))}
                  </div>
                )}
              </div>
            )}

            {/* Related Questions */}
            {message.related_questions && message.related_questions.length > 0 && (
              <div className="mt-4 pt-4 border-t border-gray-700/50">
                <button
                  onClick={() => setShowRelatedQuestions(!showRelatedQuestions)}
                  className="flex items-center space-x-2 text-white/60 hover:text-white transition-colors text-sm"
                >
                  <span className="font-medium">Related questions</span>
                  {showRelatedQuestions ? <ChevronUp className="w-4 h-4" /> : <ChevronDown className="w-4 h-4" />}
                </button>

                {showRelatedQuestions && (
                  <div className="mt-3 space-y-2">
                    {message.related_questions.map((question, idx) => (
                      <button
                        key={idx}
                        className="w-full text-left p-2 text-sm text-white/60 hover:text-emerald-400 hover:bg-gray-900/30 rounded transition-colors"
                      >
                        → {question}
                      </button>
                    ))}
                  </div>
                )}
              </div>
            )}
          </div>

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

