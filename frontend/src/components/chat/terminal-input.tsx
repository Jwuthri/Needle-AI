'use client'

import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { motion } from 'framer-motion'
import { Send, Terminal } from 'lucide-react'
import { useUser } from '@clerk/nextjs'

interface TerminalInputProps {
  onSendMessage: (message: string) => void
  disabled?: boolean
  companyName?: string
}

export function TerminalInput({ onSendMessage, disabled, companyName }: TerminalInputProps) {
  const { user } = useUser()
  const [input, setInput] = useState('')
  const [history, setHistory] = useState<string[]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const [showCursor, setShowCursor] = useState(true)
  const inputRef = useRef<HTMLInputElement>(null)
  
  const userEmail = user?.primaryEmailAddress?.emailAddress || 'user'

  // Blinking cursor effect
  useEffect(() => {
    const interval = setInterval(() => {
      setShowCursor((prev) => !prev)
    }, 530)

    return () => clearInterval(interval)
  }, [])

  const handleSubmit = (e?: React.FormEvent) => {
    e?.preventDefault()
    if (!input.trim() || disabled) return

    onSendMessage(input)
    setHistory((prev) => [...prev, input])
    setInput('')
    setHistoryIndex(-1)
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLInputElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit()
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      if (history.length > 0) {
        const newIndex = historyIndex === -1 ? history.length - 1 : Math.max(0, historyIndex - 1)
        setHistoryIndex(newIndex)
        setInput(history[newIndex])
      }
    } else if (e.key === 'ArrowDown') {
      e.preventDefault()
      if (historyIndex !== -1) {
        const newIndex = historyIndex + 1
        if (newIndex >= history.length) {
          setHistoryIndex(-1)
          setInput('')
        } else {
          setHistoryIndex(newIndex)
          setInput(history[newIndex])
        }
      }
    }
  }

  return (
    <form onSubmit={handleSubmit} className="relative">
      <div className="bg-gray-900/80 border-2 border-emerald-500/30 rounded-xl overflow-hidden hover:border-emerald-500/50 transition-colors focus-within:border-emerald-500">
        <div className="flex items-center px-4 py-3 border-b border-gray-800/50 bg-gray-800/30">
          <Terminal className="w-4 h-4 text-emerald-400 mr-2" />
          <span className="text-emerald-400 font-mono text-sm">
            {userEmail} ~ $
          </span>
        </div>

        <div 
          className="flex items-center cursor-text"
          onClick={() => inputRef.current?.focus()}
        >
          <input
            ref={inputRef}
            type="text"
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder={disabled ? 'Select a company to start...' : 'Type your query...'}
            className="flex-1 px-4 py-4 bg-transparent text-white placeholder-gray-500 focus:outline-none font-mono disabled:opacity-50 disabled:cursor-not-allowed cursor-text"
          />
          {!disabled && input && showCursor && (
            <span className="text-emerald-400 font-mono animate-pulse">▋</span>
          )}

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            type="submit"
            disabled={!input.trim() || disabled}
            className="m-2 p-3 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 disabled:from-gray-700 disabled:to-gray-700 text-white rounded-xl transition-all duration-200 disabled:scale-100 disabled:opacity-50 shadow-lg shadow-emerald-500/20 hover:shadow-xl hover:shadow-emerald-500/30 disabled:shadow-none"
          >
            <Send className="w-5 h-5" />
          </motion.button>
        </div>
      </div>

      {/* Hint */}
      <div className="mt-2 text-xs text-white/30 flex items-center justify-between font-mono">
        <span>↑↓ for history • Enter to send</span>
        <span>{input.length}/1000</span>
      </div>
    </form>
  )
}

