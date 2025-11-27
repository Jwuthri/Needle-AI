import React from 'react'
import { Wrench, CheckCircle } from 'lucide-react'
import { MarkdownRenderer } from './markdown-renderer'

// Format agent names (e.g., "DataAnalyst" -> "Data Analyst")
export function formatAgentName(name: string): string {
  if (!name) return ''
  
  // Add space before capital letters, but avoid adding space at the beginning
  // e.g. "DataAnalyst" -> "Data Analyst"
  // e.g. "Visualizer" -> "Visualizer"
  const withSpaces = name.replace(/([A-Z])/g, ' $1').trim()
  
  // If it was all caps or snake case, handle that too
  // e.g. "DATA_ANALYST" -> "Data Analyst"
  if (name === name.toUpperCase() && name.includes('_')) {
    return name.split('_')
      .map(word => word.charAt(0).toUpperCase() + word.slice(1).toLowerCase())
      .join(' ')
  }
  
  // If it was already space separated but maybe weird casing, fix it
  // But usually node names are CamelCase or SnakeCase
  
  return withSpaces
}

// Try to parse and format JSON/list objects nicely
export function formatRawOutput(rawOutput: string): JSX.Element {
  // First, try to detect if this looks like a list/dict structure
  let trimmed = rawOutput.trim()

  // Extract content from Python tool return format: content='...' name='...' tool_call_id='...'
  // This handles LangChain/LangGraph tool output format
  const contentMatch = trimmed.match(/^content=['"]([\s\S]*?)['"](?:\s+name=|\s+tool_call_id=|$)/)
  if (contentMatch) {
    // Unescape the content (Python escapes like \n, \t, etc.)
    trimmed = contentMatch[1]
      .replace(/\\n/g, '\n')
      .replace(/\\t/g, '\t')
      .replace(/\\'/g, "'")
      .replace(/\\"/g, '"')
      .replace(/\\\\/g, '\\')
  }

  // Check if content contains markdown elements
  // - Markdown tables look like: | col1 | col2 | or |:---|:---|
  // - Markdown headings: # or ## or ###
  // - Markdown lists: - or * or numbered
  // - Code blocks: ``` or `
  const hasMarkdownTable = trimmed.includes('|') && /\|[^|]+\|/.test(trimmed)
  const hasMarkdownHeading = /^#{1,6}\s/m.test(trimmed)
  const hasMarkdownList = /^[\s]*[-*+]\s/m.test(trimmed) || /^\d+\.\s/m.test(trimmed)
  const hasCodeBlock = trimmed.includes('```') || /`[^`]+`/.test(trimmed)
  
  if (hasMarkdownTable || hasMarkdownHeading || hasMarkdownList || hasCodeBlock) {
    // Render as markdown
    return <MarkdownRenderer content={trimmed} />
  }

  // Check if it starts with [ or { (JSON-like)
  if ((trimmed.startsWith('[') || trimmed.startsWith('{')) &&
    (trimmed.endsWith(']') || trimmed.endsWith('}'))) {
    try {
      // Try to parse as JSON first
      const parsed = JSON.parse(trimmed)

      // If it's an array, display as a formatted list or table
      if (Array.isArray(parsed)) {
        // If array of objects, try to render as table
        if (parsed.length > 0 && typeof parsed[0] === 'object' && parsed[0] !== null) {
          const keys = Object.keys(parsed[0])
          return (
            <div className="overflow-x-auto w-full max-w-full">
              <table className="border border-gray-700">
                <thead className="bg-gray-800">
                  <tr>
                    {keys.map((key) => (
                      <th key={key} className="px-3 py-2 text-left text-xs font-medium text-purple-300 border border-gray-700 whitespace-nowrap">
                        {key}
                      </th>
                    ))}
                  </tr>
                </thead>
                <tbody>
                  {parsed.map((row, i) => (
                    <tr key={i} className={i % 2 === 0 ? 'bg-gray-900/50' : 'bg-gray-800/30'}>
                      {keys.map((key) => (
                        <td key={key} className="px-3 py-2 text-xs text-white/80 border border-gray-700 whitespace-nowrap">
                          {typeof row[key] === 'object'
                            ? JSON.stringify(row[key])
                            : String(row[key])}
                        </td>
                      ))}
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )
        }

        // Array of primitives - render as list
        return (
          <div className="space-y-1">
            {parsed.map((item, i) => (
              <div key={i} className="flex items-start">
                <span className="text-purple-400 mr-2">•</span>
                <span className="text-white/80">{String(item)}</span>
              </div>
            ))}
          </div>
        )
      }

      // If it's an object, display as formatted JSON
      if (typeof parsed === 'object' && parsed !== null) {
        return (
          <pre className="text-xs text-white/80 whitespace-pre-wrap font-mono">
            {JSON.stringify(parsed, null, 2)}
          </pre>
        )
      }

      // Primitive value
      return <span className="text-white/80">{String(parsed)}</span>
    } catch (jsonError) {
      // JSON parse failed - try Python-style dict/list conversion
      try {
        // Replace Python-style syntax with JSON
        let jsonStr = trimmed
          .replace(/'/g, '"')  // Replace single quotes with double quotes
          .replace(/True/g, 'true')  // Replace Python True
          .replace(/False/g, 'false')  // Replace Python False
          .replace(/None/g, 'null')  // Replace Python None

        const parsed = JSON.parse(jsonStr)

        // Same rendering logic as above
        if (Array.isArray(parsed)) {
          if (parsed.length > 0 && typeof parsed[0] === 'object' && parsed[0] !== null) {
            const keys = Object.keys(parsed[0])
            return (
              <div className="overflow-x-auto w-full max-w-full">
                <table className="border border-gray-700">
                  <thead className="bg-gray-800">
                    <tr>
                      {keys.map((key) => (
                        <th key={key} className="px-3 py-2 text-left text-xs font-medium text-purple-300 border border-gray-700 whitespace-nowrap">
                          {key}
                        </th>
                      ))}
                    </tr>
                  </thead>
                  <tbody>
                    {parsed.map((row, i) => (
                      <tr key={i} className={i % 2 === 0 ? 'bg-gray-900/50' : 'bg-gray-800/30'}>
                        {keys.map((key) => (
                          <td key={key} className="px-3 py-2 text-xs text-white/80 border border-gray-700 whitespace-nowrap">
                            {typeof row[key] === 'object'
                              ? JSON.stringify(row[key])
                              : String(row[key])}
                          </td>
                        ))}
                      </tr>
                    ))}
                  </tbody>
                </table>
              </div>
            )
          }

          return (
            <div className="space-y-1">
              {parsed.map((item, i) => (
                <div key={i} className="flex items-start">
                  <span className="text-purple-400 mr-2">•</span>
                  <span className="text-white/80">{String(item)}</span>
                </div>
              ))}
            </div>
          )
        }

        if (typeof parsed === 'object' && parsed !== null) {
          return (
            <pre className="text-xs text-white/80 whitespace-pre-wrap font-mono">
              {JSON.stringify(parsed, null, 2)}
            </pre>
          )
        }

        return <span className="text-white/80">{String(parsed)}</span>
      } catch (pythonError) {
        // Both JSON and Python-style parsing failed - render as markdown
      }
    }
  }

  // Not structured data - render as markdown
  return <MarkdownRenderer content={rawOutput} />
}

// Format tool call or result content
export function formatToolContent(content: any, rawOutput?: string): JSX.Element {
  if (typeof content !== 'object') {
    return <span className="text-white/70">{String(content)}</span>
  }

  const { tool_name, tool_kwargs, output, type } = content

  return (
    <div className="space-y-2">
      {/* Tool Name */}
      <div className="flex items-center gap-2">
        <Wrench className="w-4 h-4 text-purple-400" />
        <span className="font-mono font-semibold text-purple-300">{tool_name}</span>
        {type === 'tool_call' && (
          <span className="text-xs bg-blue-500/20 text-blue-300 px-2 py-0.5 rounded">
            Calling...
          </span>
        )}
        {type === 'tool_result' && (
          <span className="text-xs bg-green-500/20 text-green-300 px-2 py-0.5 rounded flex items-center gap-1">
            <CheckCircle className="w-3 h-3" />
            Completed
          </span>
        )}
      </div>

      {/* Tool Arguments */}
      {tool_kwargs && Object.keys(tool_kwargs).length > 0 && (
        <div className="pl-6">
          <div className="text-xs text-gray-400 mb-1">Arguments:</div>
          <div className="bg-gray-800/50 rounded p-2 text-xs font-mono">
            {Object.entries(tool_kwargs).map(([key, value]) => (
              <div key={key} className="flex gap-2">
                <span className="text-blue-400">{key}:</span>
                <span className="text-white/70">{JSON.stringify(value)}</span>
              </div>
            ))}
          </div>
        </div>
      )}

      {/* Tool Output - Format nicely */}
      {rawOutput && (
        <div className="pl-6">
          <div className="text-xs text-gray-400 mb-1">Output:</div>
          <div className="bg-gray-800/50 rounded p-3 text-xs max-h-60 overflow-y-auto">
            {formatRawOutput(rawOutput)}
          </div>
        </div>
      )}
    </div>
  )
}
