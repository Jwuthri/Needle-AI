'use client'

import { useState, useRef, useEffect, KeyboardEvent } from 'react'
import { createPortal } from 'react-dom'
import { motion } from 'framer-motion'
import { Send, Terminal, Building2, Check, Database } from 'lucide-react'
import { useUser, useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'
import { Company } from '@/types/company'
import { UserDataset } from '@/types/user-dataset'

interface TerminalInputProps {
  onSendMessage: (message: string) => void
  disabled?: boolean
  companyId?: string | null
  onCompanyChange?: (companyId: string | null) => void
  datasetId?: string | null
  onDatasetChange?: (datasetId: string | null) => void
}

export function TerminalInput({ 
  onSendMessage, 
  disabled = false, 
  companyId, 
  onCompanyChange,
  datasetId,
  onDatasetChange 
}: TerminalInputProps) {
  const { user } = useUser()
  const { getToken } = useAuth()
  const [input, setInput] = useState('')
  const [history, setHistory] = useState<string[]>([])
  const [historyIndex, setHistoryIndex] = useState(-1)
  const [showCursor, setShowCursor] = useState(true)
  const [companies, setCompanies] = useState<Company[]>([])
  const [datasets, setDatasets] = useState<UserDataset[]>([])
  const [showCompanyDropdown, setShowCompanyDropdown] = useState(false)
  const [showDatasetDropdown, setShowDatasetDropdown] = useState(false)
  const [companyDropdownPosition, setCompanyDropdownPosition] = useState({ top: 0, left: 0, width: 0 })
  const [datasetDropdownPosition, setDatasetDropdownPosition] = useState({ top: 0, left: 0, width: 0 })
  const inputRef = useRef<HTMLTextAreaElement>(null)
  const companyDropdownRef = useRef<HTMLDivElement>(null)
  const datasetDropdownRef = useRef<HTMLDivElement>(null)
  const companyButtonRef = useRef<HTMLButtonElement>(null)
  const datasetButtonRef = useRef<HTMLButtonElement>(null)

  const userEmail = user?.primaryEmailAddress?.emailAddress || 'user'
  const selectedCompany = companies.find(c => c.id === companyId)
  const selectedDataset = datasets.find(d => d.id === datasetId)

  // Helper to clean up table name for display
  const cleanTableName = (tableName: string) => {
    // Remove __user_user_{UUID}_ prefix (UUID can contain letters, numbers, and dashes)
    return tableName.replace(/^__user_user_[^_]+_/, '')
  }

  // Load companies
  useEffect(() => {
    const fetchCompanies = async () => {
      try {
        const token = await getToken()
        const api = createApiClient(token)
        const companiesData = await api.listCompanies()
        console.log('[TerminalInput] Fetched companies:', companiesData)
        setCompanies(companiesData.companies || [])
      } catch (error) {
        console.error('Failed to fetch companies:', error)
      }
    }

    fetchCompanies()
  }, [getToken])

  // Load datasets
  useEffect(() => {
    const fetchDatasets = async () => {
      try {
        const token = await getToken()
        const api = createApiClient(token)
        const datasetsData = await api.listUserDatasets()
        console.log('[TerminalInput] Fetched datasets:', datasetsData)
        setDatasets(datasetsData.datasets || [])
      } catch (error) {
        console.error('Failed to fetch datasets:', error)
      }
    }

    fetchDatasets()
  }, [getToken])

  useEffect(() => {
    console.log('[TerminalInput] Props:', { companyId, onCompanyChange: !!onCompanyChange, companiesCount: companies.length })
  }, [companyId, onCompanyChange, companies])

  // Calculate dropdown positions
  const updateCompanyDropdownPosition = () => {
    if (companyButtonRef.current) {
      const rect = companyButtonRef.current.getBoundingClientRect()
      setCompanyDropdownPosition({
        top: rect.top - 8,
        left: rect.left,
        width: 288 // w-72 = 18rem = 288px
      })
    }
  }

  const updateDatasetDropdownPosition = () => {
    if (datasetButtonRef.current) {
      const rect = datasetButtonRef.current.getBoundingClientRect()
      setDatasetDropdownPosition({
        top: rect.top - 8,
        left: rect.left,
        width: 288 // w-72 = 18rem = 288px
      })
    }
  }

  // Close company dropdown when clicking outside
  useEffect(() => {
    if (!showCompanyDropdown) return

    const handleClickOutside = (event: MouseEvent) => {
      if (companyDropdownRef.current && !companyDropdownRef.current.contains(event.target as Node) &&
          companyButtonRef.current && !companyButtonRef.current.contains(event.target as Node)) {
        setShowCompanyDropdown(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showCompanyDropdown])

  // Close dataset dropdown when clicking outside
  useEffect(() => {
    if (!showDatasetDropdown) return

    const handleClickOutside = (event: MouseEvent) => {
      if (datasetDropdownRef.current && !datasetDropdownRef.current.contains(event.target as Node) &&
          datasetButtonRef.current && !datasetButtonRef.current.contains(event.target as Node)) {
        setShowDatasetDropdown(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [showDatasetDropdown])

  // Blinking cursor effect
  useEffect(() => {
    const interval = setInterval(() => {
      setShowCursor((prev) => !prev)
    }, 530)
    return () => clearInterval(interval)
  }, [])

  const handleSubmit = (e: React.FormEvent | React.KeyboardEvent) => {
    e.preventDefault()
    if (input.trim() && !disabled) {
      setHistory((prev) => [...prev, input])
      setHistoryIndex(-1)
      onSendMessage(input)
      setInput('')
    }
  }

  const handleKeyDown = (e: KeyboardEvent<HTMLTextAreaElement>) => {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      handleSubmit(e)
      return
    }

    if (e.key === 'ArrowUp') {
      if (inputRef.current && inputRef.current.selectionStart === 0 && inputRef.current.selectionEnd === 0) {
        e.preventDefault()
        if (history.length > 0) {
          const newIndex = historyIndex === -1 ? history.length - 1 : Math.max(0, historyIndex - 1)
          setHistoryIndex(newIndex)
          setInput(history[newIndex])
        }
      }
    } else if (e.key === 'ArrowDown') {
      if (inputRef.current && inputRef.current.selectionStart === input.length && inputRef.current.selectionEnd === input.length) {
        e.preventDefault()
        if (historyIndex !== -1) {
          const newIndex = Math.min(history.length - 1, historyIndex + 1)
          if (newIndex === history.length - 1 && historyIndex === history.length - 1) {
            setHistoryIndex(-1)
            setInput('')
          } else {
            setHistoryIndex(newIndex)
            setInput(history[newIndex])
          }
        }
      }
    }
  }

  // Auto-resize textarea
  useEffect(() => {
    if (inputRef.current) {
      inputRef.current.style.height = 'auto'
      inputRef.current.style.height = inputRef.current.scrollHeight + 'px'
    }
  }, [input])

  return (
    <form onSubmit={handleSubmit} className="w-full">
      <div className="relative rounded-xl bg-gradient-to-br from-gray-900 via-gray-900 to-gray-800 border border-gray-700/50 shadow-xl overflow-hidden backdrop-blur-sm ring-1 ring-white/5">
        {/* Terminal Header */}
        <div className="flex items-center justify-between px-4 py-3 border-b border-gray-700/50 bg-gray-800/40">
          <div className="flex items-center gap-3">
            <div className="flex-shrink-0 w-8 h-8 rounded-lg bg-emerald-500/10 ring-1 ring-emerald-500/30 flex items-center justify-center">
              <Terminal className="w-4 h-4 text-emerald-400" />
            </div>
            <span className="text-emerald-400 font-mono text-sm font-medium">
              {userEmail.split('@')[0]} ~ $
            </span>
          </div>

          {/* Selectors */}
          <div className="flex items-center gap-2">
            {/* Company Selector */}
            <div className="relative">
              <button
                ref={companyButtonRef}
                type="button"
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  console.log('[TerminalInput] Toggle company dropdown, current state:', showCompanyDropdown)
                  updateCompanyDropdownPosition()
                  setShowCompanyDropdown(!showCompanyDropdown)
                  setShowDatasetDropdown(false)
                }}
                className="group flex items-center gap-2 px-3 py-2 bg-gray-800/80 hover:bg-gray-800 border border-gray-700/50 hover:border-emerald-500/50 rounded-lg transition-all text-sm"
              >
                <Building2 className="w-4 h-4 text-emerald-400" />
                <span className="text-white/90 group-hover:text-white font-medium truncate max-w-[120px]">
                  {selectedCompany ? selectedCompany.name : 'Company'}
                </span>
                <svg
                  className={`w-3 h-3 text-gray-400 transition-transform ${showCompanyDropdown ? 'rotate-180' : ''}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>

            {/* Dataset Selector */}
            <div className="relative">
              <button
                ref={datasetButtonRef}
                type="button"
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  console.log('[TerminalInput] Toggle dataset dropdown, current state:', showDatasetDropdown)
                  updateDatasetDropdownPosition()
                  setShowDatasetDropdown(!showDatasetDropdown)
                  setShowCompanyDropdown(false)
                }}
                className="group flex items-center gap-2 px-3 py-2 bg-gray-800/80 hover:bg-gray-800 border border-gray-700/50 hover:border-blue-500/50 rounded-lg transition-all text-sm"
              >
                <Database className="w-4 h-4 text-blue-400" />
                <span className="text-white/90 group-hover:text-white font-medium truncate max-w-[120px]">
                  {selectedDataset ? cleanTableName(selectedDataset.table_name) : 'Dataset'}
                </span>
                <svg
                  className={`w-3 h-3 text-gray-400 transition-transform ${showDatasetDropdown ? 'rotate-180' : ''}`}
                  fill="none"
                  stroke="currentColor"
                  viewBox="0 0 24 24"
                >
                  <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                </svg>
              </button>
            </div>
          </div>
        </div>

        <div
          className="flex items-end cursor-text"
          onClick={() => inputRef.current?.focus()}
        >
          <textarea
            ref={inputRef}
            value={input}
            onChange={(e) => setInput(e.target.value)}
            onKeyDown={handleKeyDown}
            disabled={disabled}
            placeholder="Type your query..."
            rows={1}
            className="flex-1 px-4 py-4 bg-transparent text-white placeholder-gray-500 focus:outline-none font-mono disabled:opacity-50 disabled:cursor-not-allowed cursor-text resize-none overflow-hidden"
            maxLength={1000}
          />
          {!disabled && input && showCursor && (
            <span className="text-emerald-400 font-mono animate-pulse mb-4">▋</span>
          )}

          <motion.button
            whileHover={{ scale: 1.05 }}
            whileTap={{ scale: 0.95 }}
            type="submit"
            disabled={!input.trim() || disabled}
            className="m-2 p-3 bg-gradient-to-br from-emerald-600 to-emerald-700 hover:from-emerald-500 hover:to-emerald-600 disabled:from-gray-700 disabled:to-gray-800 text-white rounded-xl transition-all duration-200 disabled:scale-100 disabled:opacity-40 shadow-lg shadow-emerald-500/25 hover:shadow-xl hover:shadow-emerald-500/40 disabled:shadow-none ring-1 ring-emerald-500/20 disabled:ring-0"
          >
            <Send className="w-5 h-5" />
          </motion.button>
        </div>
      </div>

      {/* Hint */}
      <div className="mt-3 px-1 text-xs text-gray-500 flex items-center justify-between font-mono">
        <div className="flex items-center gap-3">
          <span className="flex items-center gap-1.5">
            <kbd className="px-1.5 py-0.5 bg-gray-800/50 border border-gray-700/50 rounded text-gray-400">↑↓</kbd>
            <span>history</span>
          </span>
          <span className="flex items-center gap-1.5">
            <kbd className="px-1.5 py-0.5 bg-gray-800/50 border border-gray-700/50 rounded text-gray-400">Shift + Enter</kbd>
            <span>new line</span>
          </span>
          <span className="flex items-center gap-1.5">
            <kbd className="px-1.5 py-0.5 bg-gray-800/50 border border-gray-700/50 rounded text-gray-400">Enter</kbd>
            <span>send</span>
          </span>
        </div>
        <span className={`${input.length > 900 ? 'text-orange-400' : ''} ${input.length > 950 ? 'text-red-400' : ''}`}>
          {input.length}/1000
        </span>
      </div>

      {/* Company Dropdown Portal */}
      {typeof window !== 'undefined' && showCompanyDropdown && createPortal(
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-[9998]"
            onClick={() => setShowCompanyDropdown(false)}
          />

          {/* Dropdown */}
          <div
            ref={companyDropdownRef}
            style={{
              position: 'fixed',
              top: `${companyDropdownPosition.top}px`,
              left: `${companyDropdownPosition.left}px`,
              width: `${companyDropdownPosition.width}px`,
              transform: 'translateY(-100%)',
              marginTop: '-8px',
            }}
            className="bg-gray-900 border border-gray-700 rounded-lg shadow-2xl overflow-hidden z-[9999]"
          >
            <div className="max-h-64 overflow-y-auto p-2">
              {/* No Company */}
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  console.log('[TerminalInput] No company clicked, onCompanyChange exists:', !!onCompanyChange)
                  if (onCompanyChange) {
                    onCompanyChange(null)
                  }
                  setShowCompanyDropdown(false)
                }}
                className={`w-full text-left px-3 py-2 rounded text-sm flex items-center justify-between transition-colors ${!companyId ? 'bg-emerald-500/20 text-emerald-400' : 'text-gray-300 hover:bg-gray-800'
                  }`}
              >
                <span>No company</span>
                {!companyId && <Check className="w-4 h-4" />}
              </button>

              {companies.length > 0 && <div className="my-1 h-px bg-gray-800" />}

              {/* Companies */}
              {companies.map((company) => (
                <button
                  key={company.id}
                  type="button"
                  onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    console.log('[TerminalInput] Company clicked:', company.name, company.id, 'onCompanyChange exists:', !!onCompanyChange)
                    if (onCompanyChange) {
                      onCompanyChange(company.id)
                    }
                    setShowCompanyDropdown(false)
                  }}
                  className={`w-full text-left px-3 py-2 rounded text-sm flex items-center justify-between transition-colors ${companyId === company.id ? 'bg-emerald-500/20 text-emerald-400' : 'text-gray-300 hover:bg-gray-800'
                    }`}
                >
                  <span className="truncate">{company.name}</span>
                  {companyId === company.id && <Check className="w-4 h-4 flex-shrink-0" />}
                </button>
              ))}
            </div>
          </div>
        </>,
        document.body
      )}

      {/* Dataset Dropdown Portal */}
      {typeof window !== 'undefined' && showDatasetDropdown && createPortal(
        <>
          {/* Backdrop */}
          <div
            className="fixed inset-0 z-[9998]"
            onClick={() => setShowDatasetDropdown(false)}
          />

          {/* Dropdown */}
          <div
            ref={datasetDropdownRef}
            style={{
              position: 'fixed',
              top: `${datasetDropdownPosition.top}px`,
              left: `${datasetDropdownPosition.left}px`,
              width: `${datasetDropdownPosition.width}px`,
              transform: 'translateY(-100%)',
              marginTop: '-8px',
            }}
            className="bg-gray-900 border border-gray-700 rounded-lg shadow-2xl overflow-hidden z-[9999]"
          >
            <div className="max-h-64 overflow-y-auto p-2">
              {/* No Dataset */}
              <button
                type="button"
                onClick={(e) => {
                  e.preventDefault()
                  e.stopPropagation()
                  console.log('[TerminalInput] No dataset clicked, onDatasetChange exists:', !!onDatasetChange)
                  if (onDatasetChange) {
                    onDatasetChange(null)
                  }
                  setShowDatasetDropdown(false)
                }}
                className={`w-full text-left px-3 py-2 rounded text-sm flex items-center justify-between transition-colors ${!datasetId ? 'bg-blue-500/20 text-blue-400' : 'text-gray-300 hover:bg-gray-800'
                  }`}
              >
                <span>No dataset</span>
                {!datasetId && <Check className="w-4 h-4" />}
              </button>

              {datasets.length > 0 && <div className="my-1 h-px bg-gray-800" />}

              {/* Datasets */}
              {datasets.map((dataset) => (
                <button
                  key={dataset.id}
                  type="button"
                  onClick={(e) => {
                    e.preventDefault()
                    e.stopPropagation()
                    console.log('[TerminalInput] Dataset clicked:', dataset.id, 'onDatasetChange exists:', !!onDatasetChange)
                    if (onDatasetChange) {
                      onDatasetChange(dataset.id)
                    }
                    setShowDatasetDropdown(false)
                  }}
                  className={`w-full text-left px-3 py-2 rounded text-sm flex flex-col items-start transition-colors ${datasetId === dataset.id ? 'bg-blue-500/20 text-blue-400' : 'text-gray-300 hover:bg-gray-800'
                    }`}
                >
                  <div className="w-full flex items-center justify-between">
                    <span className="truncate font-medium">
                      {cleanTableName(dataset.table_name)}
                    </span>
                    {datasetId === dataset.id && <Check className="w-4 h-4 flex-shrink-0 ml-2" />}
                  </div>
                  <span className="text-xs text-gray-500 truncate w-full">
                    {dataset.row_count.toLocaleString()} rows
                  </span>
                </button>
              ))}
            </div>
          </div>
        </>,
        document.body
      )}
    </form>
  )
}
