import React from 'react'

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

interface MarkdownRendererProps {
  content: string
  className?: string
}

export function MarkdownRenderer({ content, className = '' }: MarkdownRendererProps) {
  if (!content) return null

  // Ensure content is a string (it might be an object for structured tool calls)
  const stringContent = typeof content === 'string' ? content : JSON.stringify(content)

  // Filter out the {"next": "..."} noise that sometimes leaks from the backend
  // Matches {"next": "AgentName"} or {"next":"AgentName"} with various quotes and spacing
  const cleanContent = stringContent.replace(/\{\s*["']next["']\s*:\s*["'][^"']*["']\s*\}/gi, '')

  const lines = cleanContent.split('\n')
  const sections: JSX.Element[] = []
  let currentSection: string[] = []
  let currentTable: string[] = []
  let sectionIndex = 0

  const flushSection = () => {
    if (currentSection.length > 0) {
      sections.push(
        <div key={`section-${sectionIndex++}`} className="mb-3 last:mb-0">
          <p className="text-white/90 whitespace-pre-wrap leading-relaxed">{parseInlineMarkdown(currentSection.join('\n'))}</p>
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
          <div key={`table-${sectionIndex++}`} className="mb-4 overflow-x-auto max-w-full">
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
      
      // Convert local file path to API endpoint logic (simplified for display)
      let imageUrl = imagePath
      if (!imagePath.startsWith('http')) {
         // Simple heuristic for relative paths
         const baseUrl = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'
         const apiBase = baseUrl.endsWith('/api/v1') ? baseUrl : `${baseUrl}/api/v1`
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

    // Detect horizontal rules
    if (/^(\-{3,}|\*{3,}|_{3,})$/.test(trimmedLine)) {
      flushSection()
      sections.push(
        <hr key={`hr-${idx}`} className="border-t border-gray-700/50 my-4" />
      )
      return
    }

    // Detect bullet points
    if (trimmedLine.startsWith('-') || trimmedLine.startsWith('•') || trimmedLine.startsWith('*')) {
      const bulletMatch = trimmedLine.match(/^[-•*]\s+(.+)/)
      if (bulletMatch) {
        flushSection()
        
        // Calculate indentation
        const leadingSpaces = line.search(/\S/)
        const indentLevel = Math.floor(leadingSpaces / 2)
        const marginLeft = indentLevel > 0 ? `${indentLevel * 1.5}rem` : '0'
        
        let content = bulletMatch[1]
        if (content.endsWith(':')) content = content.slice(0, -1)

        sections.push(
          <div key={`bullet-${idx}`} className="flex items-start mb-2" style={{ marginLeft }}>
            <span className="text-purple-400 mr-2 flex-shrink-0 mt-1">•</span>
            <span className="text-white/90 flex-1">{parseInlineMarkdown(content)}</span>
          </div>
        )
        return
      }
    }
    // Detect numbered lists
    else if (trimmedLine.match(/^\d+\.\s+/)) {
      const numberMatch = trimmedLine.match(/^(\d+)\.\s+(.+)/)
      if (numberMatch) {
        flushSection()
        sections.push(
          <div key={`num-${idx}`} className="flex items-start mb-2">
            <span className="text-purple-400 mr-2 font-mono font-bold flex-shrink-0 mt-0.5">{numberMatch[1]}.</span>
            <span className="text-white/90 flex-1">{parseInlineMarkdown(numberMatch[2])}</span>
          </div>
        )
        return
      }
    }
    // Detect markdown headers
    else if (trimmedLine.startsWith('#')) {
      flushSection()
      const headerMatch = trimmedLine.match(/^(#{1,6})\s+(.+)/)
      if (headerMatch) {
        const level = headerMatch[1].length
        const headerText = headerMatch[2]

        if (level === 1) {
          sections.push(
            <h1 key={`header-${idx}`} className="text-2xl font-bold text-transparent bg-clip-text bg-gradient-to-r from-purple-400 to-blue-400 mb-3 mt-5 pb-2 border-b border-purple-500/30">
              {parseInlineMarkdown(headerText)}
            </h1>
          )
        } else if (level === 2) {
          sections.push(
            <h2 key={`header-${idx}`} className="text-xl font-bold text-white mb-3 mt-4 pl-3 border-l-4 border-purple-400">
              {parseInlineMarkdown(headerText)}
            </h2>
          )
        } else {
          sections.push(
            <h3 key={`header-${idx}`} className="text-lg font-semibold text-white/90 mb-2 mt-3">
              {parseInlineMarkdown(headerText)}
            </h3>
          )
        }
      }
    }
    // Code blocks
    else if (trimmedLine.startsWith('```')) {
      flushSection()
      sections.push(
        <div key={`code-${idx}`} className="bg-gray-950/50 border border-gray-800 rounded-lg p-3 mb-3 font-mono text-sm text-blue-300 overflow-x-auto">
          {trimmedLine.replace(/```/g, '')}
        </div>
      )
    }
    // Regular text
    else if (trimmedLine) {
      currentSection.push(trimmedLine)
    }
    // Empty line
    else if (currentSection.length > 0) {
      flushSection()
    }
  })

  flushTable()
  flushSection()

  return <div className={className}>{sections.length > 0 ? sections : <p className="text-white/80">{content}</p>}</div>
}

