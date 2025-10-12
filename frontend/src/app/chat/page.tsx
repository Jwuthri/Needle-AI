'use client'

import { useState, useEffect } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { MessageSquare, GitBranch } from 'lucide-react'
import { ChatView } from '@/components/chat/chat-view'
import { TreeView } from '@/components/chat/tree-view'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'
import { Company } from '@/types/company'

type ViewMode = 'chat' | 'tree'

export default function ChatPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const [viewMode, setViewMode] = useState<ViewMode>('chat')
  const [selectedCompany, setSelectedCompany] = useState<string | null>(
    searchParams.get('company_id')
  )
  const [companies, setCompanies] = useState<Company[]>([])
  const [sessionId, setSessionId] = useState<string>()

  // Redirect to sign-in if not authenticated
  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.push('/sign-in')
    }
  }, [isLoaded, isSignedIn, router])

  useEffect(() => {
    const fetchCompanies = async () => {
      if (!isSignedIn) return
      
      try {
        const token = await getToken()
        const api = createApiClient(token)
        const data = await api.listCompanies()
        setCompanies(data.companies || [])
      } catch (error) {
        console.error('Failed to fetch companies:', error)
      }
    }

    fetchCompanies()
  }, [getToken, isSignedIn])

  // Show loading state while checking authentication
  if (!isLoaded || !isSignedIn) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-950">
        <div className="text-gray-400">Loading...</div>
      </div>
    )
  }

  return (
    <div className="h-screen flex flex-col bg-gray-950">
      {/* Header */}
      <header className="flex items-center justify-between px-6 py-4 border-b border-gray-800/50">
        <div className="flex items-center space-x-6">
          <h1 className="text-xl font-bold text-white">Chat</h1>

          {/* Company Selector */}
          <select
            value={selectedCompany || ''}
            onChange={(e) => setSelectedCompany(e.target.value || null)}
            className="px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
          >
            <option value="">Select a company...</option>
            {companies.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name}
              </option>
            ))}
          </select>
        </div>

        {/* View Toggle */}
        <div className="flex items-center space-x-2 bg-gray-800/50 rounded-lg p-1">
          <button
            onClick={() => setViewMode('chat')}
            className={`
              flex items-center space-x-2 px-4 py-2 rounded-md transition-all
              ${
                viewMode === 'chat'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'text-gray-400 hover:text-white'
              }
            `}
          >
            <MessageSquare className="w-4 h-4" />
            <span className="font-medium">Chat</span>
          </button>
          <button
            onClick={() => setViewMode('tree')}
            className={`
              flex items-center space-x-2 px-4 py-2 rounded-md transition-all
              ${
                viewMode === 'tree'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'text-gray-400 hover:text-white'
              }
            `}
          >
            <GitBranch className="w-4 h-4" />
            <span className="font-medium">Tree</span>
          </button>
        </div>
      </header>

      {/* Main Content */}
      <div className="flex-1 overflow-hidden">
        {viewMode === 'chat' ? (
          <ChatView
            companyId={selectedCompany}
            sessionId={sessionId}
            onSessionIdChange={setSessionId}
          />
        ) : (
          <TreeView
            companyId={selectedCompany}
            sessionId={sessionId}
          />
        )}
      </div>
    </div>
  )
}
