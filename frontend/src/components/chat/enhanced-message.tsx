'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { User, Sparkles, ChevronDown, ChevronUp, ExternalLink, Copy, ThumbsUp, ThumbsDown } from 'lucide-react'
import { EnhancedChatMessage } from '@/types/chat'

interface EnhancedMessageProps {
  message: EnhancedChatMessage
  onQuestionClick?: (question: string) => void
}

// Keyword categories for highlighting
const KEYWORDS = {
  actions: ['count', 'sum', 'average', 'calculate', 'analyze', 'show', 'list', 'find', 'get', 'search', 'filter', 'group', 'aggregate'],
  entities: ['transactions', 'users', 'customers', 'payments', 'reviews', 'products', 'orders', 'data', 'records'],
  methods: ['card', 'paypal', 'cash', 'credit', 'debit', 'bank', 'transfer', 'wallet'],
  metrics: ['total', 'revenue', 'sales', 'amount', 'quantity', 'rate', 'percentage', 'ratio', 'score'],
}

// Highlight keywords in text
const highlightKeywords = (text: string) => {
  let result = text
  const highlights: Array<{ text: string; color: string; start: number; end: number }> = []

  // Find all keyword matches
  Object.entries(KEYWORDS).forEach(([category, words]) => {
    words.forEach((word) => {
      const regex = new RegExp(`\\b(${word})\\b`, 'gi')
      let match
      while ((match = regex.exec(text)) !== null) {
        const color = 
          category === 'actions' ? 'text-blue-400' :
          category === 'entities' ? 'text-emerald-400' :
          category === 'methods' ? 'text-purple-400' :
          'text-yellow-400'
        
        highlights.push({
          text: match[0],
          color,
          start: match.index,
          end: match.index + match[0].length
        })
      }
    })
  })

  // Sort by position and remove overlaps
  highlights.sort((a, b) => a.start - b.start)
  const filtered = highlights.filter((h, i) => {
    if (i === 0) return true
    return h.start >= highlights[i - 1].end
  })

  // Build JSX with highlights
  const parts: JSX.Element[] = []
  let lastIndex = 0

  filtered.forEach((h, i) => {
    if (h.start > lastIndex) {
      parts.push(<span key={`text-${i}`}>{text.slice(lastIndex, h.start)}</span>)
    }
    parts.push(
      <span key={`highlight-${i}`} className={`font-semibold ${h.color}`}>
        {h.text}
      </span>
    )
    lastIndex = h.end
  })

  if (lastIndex < text.length) {
    parts.push(<span key="text-final">{text.slice(lastIndex)}</span>)
  }

  return parts.length > 0 ? <>{parts}</> : text
}

// Format assistant responses with structure
const formatAssistantContent = (content: string) => {
  const lines = content.split('\n')
  const sections: JSX.Element[] = []
  let currentSection: string[] = []
  let sectionIndex = 0

  lines.forEach((line, idx) => {
    const trimmedLine = line.trim()
    
    // Detect markdown headers (##, ###, etc.)
    if (trimmedLine.startsWith('#')) {
      if (currentSection.length > 0) {
        sections.push(
          <div key={`section-${sectionIndex++}`} className="mb-4">
            <p className="text-white/80">{highlightKeywords(currentSection.join(' '))}</p>
          </div>
        )
        currentSection = []
      }
      
      // Count # symbols to determine header level
      const headerMatch = trimmedLine.match(/^(#{1,6})\s+(.+)/)
      if (headerMatch) {
        const level = headerMatch[1].length
        const headerText = headerMatch[2]
        const headerClass = level === 1 ? 'text-2xl' : level === 2 ? 'text-xl' : 'text-lg'
        
        sections.push(
          <h3 key={`header-${idx}`} className={`${headerClass} font-semibold text-white mb-3 mt-2 flex items-center`}>
            <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full mr-2"></span>
            {headerText}
          </h3>
        )
      }
    }
    // Detect headers (lines ending with :)
    else if (trimmedLine.endsWith(':') && trimmedLine.length > 3 && !trimmedLine.includes('http')) {
      if (currentSection.length > 0) {
        sections.push(
          <div key={`section-${sectionIndex++}`} className="mb-4">
            <p className="text-white/80">{highlightKeywords(currentSection.join(' '))}</p>
          </div>
        )
        currentSection = []
      }
      sections.push(
        <h3 key={`header-${idx}`} className="text-lg font-semibold text-white mb-2 flex items-center">
          <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full mr-2"></span>
          {trimmedLine.replace(':', '')}
        </h3>
      )
    }
    // Detect bullet points (markdown or unicode)
    else if (trimmedLine.startsWith('-') || trimmedLine.startsWith('•') || trimmedLine.startsWith('*')) {
      if (currentSection.length > 0) {
        sections.push(
          <div key={`section-${sectionIndex++}`} className="mb-4">
            <p className="text-white/80">{highlightKeywords(currentSection.join(' '))}</p>
          </div>
        )
        currentSection = []
      }
      sections.push(
        <div key={`bullet-${idx}`} className="flex items-start mb-2">
          <span className="text-emerald-400 mr-2">•</span>
          <span className="text-white/80">{highlightKeywords(trimmedLine.replace(/^[-•*]\s*/, ''))}</span>
        </div>
      )
    }
    // Code blocks
    else if (trimmedLine.startsWith('```')) {
      if (currentSection.length > 0) {
        sections.push(
          <div key={`section-${sectionIndex++}`} className="mb-4">
            <p className="text-white/80">{highlightKeywords(currentSection.join(' '))}</p>
          </div>
        )
        currentSection = []
      }
      sections.push(
        <div key={`code-${idx}`} className="bg-gray-900/50 border border-gray-700/30 rounded-lg p-3 mb-2 font-mono text-sm text-emerald-300">
          {trimmedLine.replace(/```/g, '')}
        </div>
      )
    }
    // Regular text
    else if (trimmedLine) {
      currentSection.push(trimmedLine)
    }
    // Empty line - flush current section
    else if (currentSection.length > 0) {
      sections.push(
        <div key={`section-${sectionIndex++}`} className="mb-4">
          <p className="text-white/80">{highlightKeywords(currentSection.join(' '))}</p>
        </div>
      )
      currentSection = []
    }
  })

  // Flush remaining content
  if (currentSection.length > 0) {
    sections.push(
      <div key={`section-${sectionIndex}`} className="mb-4">
        <p className="text-white/80">{highlightKeywords(currentSection.join(' '))}</p>
      </div>
    )
  }

  return sections.length > 0 ? sections : [<p key="default" className="text-white/80">{content}</p>]
}

export function EnhancedMessage({ message, onQuestionClick }: EnhancedMessageProps) {
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

  // User message - show as a question card
  if (isUser) {
    return (
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        className="mb-8"
      >
        <div className="bg-gradient-to-br from-blue-500/10 to-purple-500/10 border border-blue-500/30 rounded-2xl p-6">
          <div className="flex items-start space-x-3">
            <div className="w-10 h-10 rounded-xl bg-blue-500/20 flex items-center justify-center flex-shrink-0">
              <User className="w-5 h-5 text-blue-400" />
            </div>
            <div className="flex-1">
              <h2 className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-blue-400 to-cyan-400 mb-2">
                {highlightKeywords(message.content)}
              </h2>
              {message.query_type && (
                <p className="text-white/60 text-sm">
                  Analyzing {message.query_type.replace('_', ' ')}...
                </p>
              )}
            </div>
            <button
              onClick={() => navigator.clipboard.writeText(message.content)}
              className="p-2 text-white/40 hover:text-white transition-colors rounded-lg hover:bg-white/5"
            >
              <Copy className="w-4 h-4" />
            </button>
          </div>
        </div>
      </motion.div>
    )
  }

  // Assistant message - show as structured response
  return (
    <motion.div
      initial={{ opacity: 0, y: 20 }}
      animate={{ opacity: 1, y: 0 }}
      className="mb-8"
    >
      <div className="flex items-start space-x-3">
        <div className="w-10 h-10 rounded-xl bg-gradient-to-br from-emerald-500 to-green-600 flex items-center justify-center flex-shrink-0">
          <Sparkles className="w-5 h-5 text-white" />
        </div>

        <div className="flex-1">
          {/* Main Response */}
          <div className={`rounded-2xl p-6 ${
            message.error
              ? 'bg-red-500/10 border border-red-500/30'
              : 'bg-gray-800/50 border border-gray-700/50'
          }`}>
            {/* Summary if first line is short and not a markdown header */}
            {!message.error && 
             !message.content.split('\n')[0].trim().startsWith('#') && 
             message.content.split('\n')[0].length < 100 && 
             message.content.split('\n')[0].length > 0 && (
              <div className="mb-4 pb-4 border-b border-gray-700/30">
                <p className="text-white/60 text-sm">
                  {message.content.split('\n')[0]}
                </p>
              </div>
            )}

            {/* Formatted content */}
            <div className="space-y-4">
              {formatAssistantContent(message.content)}
            </div>

            {/* Query Type Badge */}
            {message.query_type && (
              <div className="mt-4 inline-flex items-center px-3 py-1 bg-emerald-500/10 border border-emerald-500/30 rounded-xl text-emerald-400 text-xs font-medium">
                {message.query_type.replace('_', ' ').toUpperCase()}
              </div>
            )}
          </div>

          {/* Agent Steps are now shown above the message, not inside it */}

          {/* Sources Section */}
          {message.sources && message.sources.length > 0 && (
            <div className="mt-4 bg-gray-900/50 border border-gray-700/30 rounded-xl overflow-hidden">
              <button
                onClick={() => setShowSources(!showSources)}
                className="w-full flex items-center justify-between p-4 hover:bg-gray-800/30 transition-colors"
              >
                <div className="flex items-center space-x-2">
                  <div className="w-6 h-6 rounded-lg bg-emerald-500/10 flex items-center justify-center">
                    <span className="text-xs font-bold text-emerald-400">{message.sources.length}</span>
                  </div>
                  <span className="text-white font-medium">Sources</span>
                </div>
                {showSources ? <ChevronUp className="w-5 h-5 text-white/60" /> : <ChevronDown className="w-5 h-5 text-white/60" />}
              </button>

              {showSources && (
                <div className="p-4 pt-0 space-y-3">
                  {message.sources.map((source) => (
                    <div
                      key={source.review_id}
                      className="p-4 bg-gray-800/50 border border-gray-700/30 rounded-xl hover:border-emerald-500/30 transition-colors"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div className="flex items-center space-x-2">
                          <span className="text-white/90 text-sm font-medium">{source.author}</span>
                          <span className="text-white/30">•</span>
                          <span className="text-white/50 text-xs">{source.source}</span>
                          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${
                            source.sentiment > 0.5 ? 'bg-green-500/10 text-green-400' :
                            source.sentiment < -0.5 ? 'bg-red-500/10 text-red-400' :
                            'bg-yellow-500/10 text-yellow-400'
                          }`}>
                            {getSentimentLabel(source.sentiment)}
                          </span>
                        </div>
                        {source.url && (
                          <a
                            href={source.url}
                            target="_blank"
                            rel="noopener noreferrer"
                            className="text-emerald-400 hover:text-emerald-300 transition-colors"
                          >
                            <ExternalLink className="w-4 h-4" />
                          </a>
                        )}
                      </div>
                      <p className="text-white/70 text-sm leading-relaxed">{source.content}</p>
                      <div className="mt-2 flex items-center justify-between">
                        <span className="text-xs text-white/40">
                          Relevance: {(source.relevance_score * 100).toFixed(0)}%
                        </span>
                      </div>
                    </div>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Related Questions */}
          {message.related_questions && message.related_questions.length > 0 && (
            <div className="mt-4 bg-gray-900/50 border border-gray-700/30 rounded-xl overflow-hidden">
              <button
                onClick={() => setShowRelatedQuestions(!showRelatedQuestions)}
                className="w-full flex items-center justify-between p-4 hover:bg-gray-800/30 transition-colors"
              >
                <span className="text-white font-medium">Related Questions</span>
                {showRelatedQuestions ? <ChevronUp className="w-5 h-5 text-white/60" /> : <ChevronDown className="w-5 h-5 text-white/60" />}
              </button>

              {showRelatedQuestions && (
                <div className="p-4 pt-0 space-y-2">
                  {message.related_questions.map((question, idx) => (
                    <button
                      key={idx}
                      onClick={() => onQuestionClick?.(question)}
                      className="w-full text-left p-3 text-sm text-white/70 hover:text-emerald-400 hover:bg-gray-800/50 rounded-xl transition-all group"
                    >
                      <span className="text-emerald-400 mr-2 group-hover:mr-3 transition-all">→</span>
                      {highlightKeywords(question)}
                    </button>
                  ))}
                </div>
              )}
            </div>
          )}

          {/* Message Actions */}
          {!message.error && (
            <div className="flex items-center space-x-2 mt-4">
              <button className="p-2 text-white/40 hover:text-green-400 hover:bg-green-400/10 rounded-lg transition-all">
                <ThumbsUp className="w-4 h-4" />
              </button>
              <button className="p-2 text-white/40 hover:text-red-400 hover:bg-red-400/10 rounded-lg transition-all">
                <ThumbsDown className="w-4 h-4" />
              </button>
              <button
                onClick={() => navigator.clipboard.writeText(message.content)}
                className="p-2 text-white/40 hover:text-white hover:bg-white/5 rounded-lg transition-all"
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

