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

// Parse markdown inline formatting (bold, italic)
const parseInlineMarkdown = (text: string): (string | JSX.Element)[] => {
  const parts: (string | JSX.Element)[] = []
  let currentIndex = 0
  let keyIndex = 0

  // Match **bold** and *italic* patterns
  const pattern = /(\*\*(.+?)\*\*)|(\*(.+?)\*)/g
  let match

  while ((match = pattern.exec(text)) !== null) {
    // Add text before the match
    if (match.index > currentIndex) {
      parts.push(text.slice(currentIndex, match.index))
    }

    // Add the formatted match
    if (match[1]) {
      // Bold: **text**
      parts.push(<strong key={`bold-${keyIndex++}`} className="font-bold text-white">{match[2]}</strong>)
    } else if (match[3]) {
      // Italic: *text*
      parts.push(<em key={`italic-${keyIndex++}`} className="italic text-white/90">{match[4]}</em>)
    }

    currentIndex = pattern.lastIndex
  }

  // Add remaining text
  if (currentIndex < text.length) {
    parts.push(text.slice(currentIndex))
  }

  return parts.length > 0 ? parts : [text]
}

// Format assistant responses with structure
const formatAssistantContent = (content: string) => {
  if (!content) return []
  const lines = content.split('\n')
  const sections: JSX.Element[] = []
  let currentSection: string[] = []
  let currentTable: string[] = []
  let sectionIndex = 0

  const flushSection = () => {
    if (currentSection.length > 0) {
      sections.push(
        <div key={`section-${sectionIndex++}`} className="mb-4">
          <p className="text-white/80 whitespace-pre-wrap">{parseInlineMarkdown(currentSection.join('\n'))}</p>
        </div>
      )
      currentSection = []
    }
  }

  const flushTable = () => {
    if (currentTable.length > 0) {
      const tableLines = currentTable.filter(l => !l.match(/^\s*\|[\s-:|]+\|\s*$/)) // Remove separator lines
      if (tableLines.length > 0) {
        const headers = tableLines[0].split('|').map(h => h.trim()).filter(h => h)
        const rows = tableLines.slice(1).map(row =>
          row.split('|').map(c => c.trim()).filter(c => c)
        ).filter(row => row.length > 0)

        sections.push(
          <div key={`table-${sectionIndex++}`} className="mb-4 overflow-x-auto w-full max-w-full">
            <table className="border border-gray-700/30 rounded-lg overflow-hidden">
              <thead className="bg-gray-800/50">
                <tr>
                  {headers.map((header, i) => (
                    <th key={i} className="px-4 py-2 text-left text-xs font-semibold text-emerald-400 border-b border-gray-700/30 whitespace-nowrap">
                      {parseInlineMarkdown(header)}
                    </th>
                  ))}
                </tr>
              </thead>
              <tbody className="bg-gray-900/30">
                {rows.map((row, i) => (
                  <tr key={i} className="border-b border-gray-700/20 hover:bg-gray-800/20">
                    {row.map((cell, j) => (
                      <td key={j} className="px-4 py-2 text-sm text-white/80 whitespace-nowrap">
                        {parseInlineMarkdown(cell)}
                      </td>
                    ))}
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        )
      }
      currentTable = []
    }
  }

  lines.forEach((line, idx) => {
    const trimmedLine = line.trim()

    // Detect markdown images: ![alt text](url)
    const imageMatch = trimmedLine.match(/!\[([^\]]*)\]\(([^)]+)\)/)
    if (imageMatch) {
      flushSection()
      const altText = imageMatch[1]
      const imagePath = imageMatch[2]

      // Convert local file path to API endpoint
      // Note: NEXT_PUBLIC_API_URL may or may not include /api/v1
      const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
      const apiBase = baseUrl.endsWith('/api/v1') ? baseUrl : `${baseUrl}/api/v1`

      let imageUrl = imagePath
      if (imagePath.startsWith('/Users/') || imagePath.startsWith('/app/')) {
        // Extract filename from full path
        const filename = imagePath.split('/').pop()
        imageUrl = `${apiBase}/graphs/${filename}`
      } else if (imagePath.startsWith('/api/graphs/')) {
        // Fix path to include /v1/
        const filename = imagePath.replace('/api/graphs/', '')
        imageUrl = `${apiBase}/graphs/${filename}`
      } else if (!imagePath.startsWith('http')) {
        // Relative path - assume it's in graphs
        const filename = imagePath.split('/').pop()
        imageUrl = `${apiBase}/graphs/${filename}`
      }

      sections.push(
        <div key={`image-${idx}`} className="my-4 rounded-lg overflow-hidden border border-gray-700/30 bg-gray-900/30">
          <img
            src={imageUrl}
            alt={altText}
            className="w-full h-auto"
            onError={(e) => {
              console.error('Failed to load image:', imageUrl)
              e.currentTarget.style.display = 'none'
            }}
          />
          {altText && (
            <div className="p-3 bg-gray-800/50 text-sm text-white/60 italic">
              {altText}
            </div>
          )}
        </div>
      )
      return
    }

    // Detect markdown table rows
    if (trimmedLine.startsWith('|') && trimmedLine.endsWith('|')) {
      flushSection()
      currentTable.push(trimmedLine)
      return
    }

    // If we were building a table and hit non-table line, flush it
    if (currentTable.length > 0) {
      flushTable()
    }

    // Detect horizontal rules (----, ****, ____) - CHECK BEFORE bullets
    if (/^(\-{3,}|\*{3,}|_{3,})$/.test(trimmedLine)) {
      flushSection()
      sections.push(
        <hr key={`hr-${idx}`} className="border-t border-gray-700/50 my-4" />
      )
      return
    }

    // Detect underline-style headers (check if next line is === or ---)
    if (idx < lines.length - 1) {
      const nextLine = lines[idx + 1].trim()
      if (trimmedLine && (/^={3,}$/.test(nextLine) || /^-{3,}$/.test(nextLine))) {
        flushSection()
        const isH1 = /^={3,}$/.test(nextLine)
        if (isH1) {
          sections.push(
            <h1 key={`header-${idx}`} className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400 mb-4 mt-6 pb-2 border-b border-emerald-500/30">
              {parseInlineMarkdown(trimmedLine)}
            </h1>
          )
        } else {
          sections.push(
            <h2 key={`header-${idx}`} className="text-xl font-bold text-white mb-3 mt-5 pl-3 border-l-4 border-emerald-400">
              {parseInlineMarkdown(trimmedLine)}
            </h2>
          )
        }
        // Skip the next line (the underline) by marking it processed
        lines[idx + 1] = '' // Clear it so it doesn't get processed
        return
      }
    }

    // Detect bullet points (markdown or unicode) - CHECK THIS AFTER horizontal rules
    if (trimmedLine.startsWith('-') || trimmedLine.startsWith('•') || trimmedLine.startsWith('*')) {
      // Make sure it's actually a bullet with content, not a horizontal rule
      const bulletMatch = trimmedLine.match(/^[-•*]\s+(.+)/)
      if (bulletMatch) {
        flushSection()

        // Calculate indentation level (spaces before the bullet)
        const leadingSpaces = line.search(/\S/)
        const indentLevel = Math.floor(leadingSpaces / 2) // 2 spaces = 1 indent level
        const marginLeft = indentLevel > 0 ? `${indentLevel * 1.5}rem` : '0'

        // Get content after the bullet
        let content = bulletMatch[1]

        // If content ends with :, remove it (it's a bullet header, not a real header)
        if (content.endsWith(':')) content = content.slice(0, -1)

        sections.push(
          <div key={`bullet-${idx}`} className="flex items-start mb-2" style={{ marginLeft }}>
            <span className="text-emerald-400 mr-2 flex-shrink-0">•</span>
            <span className="text-white/80 flex-1">{parseInlineMarkdown(content)}</span>
          </div>
        )
        return
      }
    }
    // Detect markdown headers (##, ###, etc.)
    else if (trimmedLine.startsWith('#')) {
      flushSection()

      // Count # symbols to determine header level
      const headerMatch = trimmedLine.match(/^(#{1,6})\s+(.+)/)
      if (headerMatch) {
        const level = headerMatch[1].length
        const headerText = headerMatch[2]

        // Different styling based on header level
        if (level === 1) {
          // H1: Most prominent with gradient and border
          sections.push(
            <h1 key={`header-${idx}`} className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-emerald-400 to-cyan-400 mb-4 mt-6 pb-2 border-b border-emerald-500/30">
              {parseInlineMarkdown(headerText)}
            </h1>
          )
        } else if (level === 2) {
          // H2: Bold with left border accent
          sections.push(
            <h2 key={`header-${idx}`} className="text-xl font-bold text-white mb-3 mt-5 pl-3 border-l-4 border-emerald-400">
              {parseInlineMarkdown(headerText)}
            </h2>
          )
        } else {
          // H3+: Simpler styling with subtle accent
          sections.push(
            <h3 key={`header-${idx}`} className="text-lg font-semibold text-white/90 mb-2 mt-4">
              {parseInlineMarkdown(headerText)}
            </h3>
          )
        }
      }
    }
    // Detect headers (lines ending with :) - but not long sentences
    else if (trimmedLine.endsWith(':') && trimmedLine.length > 3 && trimmedLine.length < 80 && !trimmedLine.includes('http') && !trimmedLine.includes(',')) {
      flushSection()
      sections.push(
        <h3 key={`header-${idx}`} className="text-lg font-semibold text-white mb-2 flex items-center">
          <span className="w-1.5 h-1.5 bg-emerald-400 rounded-full mr-2"></span>
          {parseInlineMarkdown(trimmedLine.replace(':', ''))}
        </h3>
      )
    }
    // Code blocks
    else if (trimmedLine.startsWith('```')) {
      flushSection()
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
      flushSection()
    }
  })

  // Flush any remaining content
  flushTable()
  flushSection()

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

        <div className="flex-1 min-w-0 max-w-full overflow-hidden">
          {/* Main Response */}
          <div className={`rounded-2xl p-6 max-h-[1000px] overflow-auto w-full ${message.error
            ? 'bg-red-500/10 border border-red-500/30'
            : 'bg-gray-800/50 border border-gray-700/50'
            }`}>
            {/* Summary if first line is short and not a markdown header */}
            {!message.error &&
              message.content &&
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
                          <span className={`text-xs font-medium px-2 py-0.5 rounded-full ${source.sentiment > 0.5 ? 'bg-green-500/10 text-green-400' :
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
            <div className="flex items-center justify-between mt-4">
              <div className="flex items-center space-x-2">
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

              {/* Execution Time */}
              {(() => {
                console.log('Message timing data:', {
                  id: message.id,
                  timestamp: message.timestamp,
                  completed_at: message.completed_at,
                  role: message.role
                })

                if (message.completed_at && message.timestamp) {
                  const completedMs = new Date(message.completed_at).getTime()
                  const createdMs = new Date(message.timestamp).getTime()
                  const executionTimeMs = completedMs - createdMs
                  const executionTimeSec = (executionTimeMs / 1000).toFixed(2)

                  return (
                    <div className="flex items-center space-x-1">
                      <div className="w-1.5 h-1.5 rounded-full bg-emerald-400"></div>
                      <span className="text-xs text-emerald-400/80 font-medium">Finished in {executionTimeSec}s</span>
                    </div>
                  )
                }
                return null
              })()}
            </div>
          )}
        </div>
      </div>
    </motion.div>
  )
}

