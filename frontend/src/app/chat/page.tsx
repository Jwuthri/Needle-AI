'use client'

import { useState, useEffect } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { MessageSquare, GitBranch, Plus, History } from 'lucide-react'
import { ChatView } from '@/components/chat/chat-view'
import { TreeView } from '@/components/chat/tree-view'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'
import { Company } from '@/types/company'
import { ChatSession } from '@/types/chat'

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
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [showSidebar, setShowSidebar] = useState(true)

  // Redirect to sign-in if not authenticated
  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.push('/sign-in')
    }
  }, [isLoaded, isSignedIn, router])

  useEffect(() => {
    const fetchData = async () => {
      if (!isSignedIn) return
      
      try {
        const token = await getToken()
        const api = createApiClient(token)
        
        // Fetch companies
        const companiesData = await api.listCompanies()
        setCompanies(companiesData.companies || [])
        
        // Fetch sessions
        const sessionsData = await api.listSessions()
        setSessions(sessionsData.sessions || [])
      } catch (error) {
        console.error('Failed to fetch data:', error)
      }
    }

    fetchData()
  }, [getToken, isSignedIn])
  
  const handleNewChat = () => {
    setSessionId(undefined)
  }
  
  const handleSelectSession = (session: ChatSession) => {
    setSessionId(session.session_id)
  }
  
  const handleSessionUpdate = (updatedSessionId: string) => {
    setSessionId(updatedSessionId)
    // Refresh sessions list
    const refreshSessions = async () => {
      try {
        const token = await getToken()
        const api = createApiClient(token)
        const sessionsData = await api.listSessions()
        setSessions(sessionsData.sessions || [])
      } catch (error) {
        console.error('Failed to refresh sessions:', error)
      }
    }
    refreshSessions()
  }

  // Show loading state while checking authentication
  if (!isLoaded || !isSignedIn) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-950">
        <div className="text-gray-400">Loading...</div>
      </div>
    )
  }

  return (
    <div className="h-screen flex bg-gray-950">
      {/* Sidebar */}
      {showSidebar && (
        <div className="w-80 border-r border-gray-800/50 flex flex-col">
          {/* Sidebar Header */}
          <div className="p-4 border-b border-gray-800/50">
            <button
              onClick={handleNewChat}
              className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 rounded-xl transition-all border border-emerald-500/30"
            >
              <Plus className="w-4 h-4" />
              <span className="font-medium">New Chat</span>
            </button>
          </div>
          
          {/* Company Selector */}
          <div className="p-4 border-b border-gray-800/50">
            <label className="text-xs text-gray-400 mb-2 block">Company Context</label>
            <select
              value={selectedCompany || ''}
              onChange={(e) => setSelectedCompany(e.target.value || null)}
              className="w-full px-3 py-2 bg-gray-800/50 border border-gray-700 rounded-lg text-white text-sm focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
            >
              <option value="">No company selected</option>
              {companies.map((company) => (
                <option key={company.id} value={company.id}>
                  {company.name}
                </option>
              ))}
            </select>
          </div>

          {/* Sessions List */}
          <div className="flex-1 overflow-y-auto">
            <div className="p-4">
              <div className="flex items-center space-x-2 mb-3">
                <History className="w-4 h-4 text-gray-400" />
                <h2 className="text-sm font-medium text-gray-400">Recent Chats</h2>
              </div>
              
              {sessions.length === 0 ? (
                <p className="text-sm text-gray-500 text-center py-8">No previous chats</p>
              ) : (
                <div className="space-y-2">
                  {sessions.map((session) => {
                    const title = session.metadata?.title || session.messages[0]?.content.substring(0, 40) || 'New Chat'
                    const companyId = session.metadata?.company_id
                    const companyName = companies.find(c => c.id === companyId)?.name
                    
                    return (
                      <button
                        key={session.session_id}
                        onClick={() => handleSelectSession(session)}
                        className={`
                          w-full text-left px-3 py-2 rounded-lg transition-all
                          ${
                            sessionId === session.session_id
                              ? 'bg-emerald-500/20 border border-emerald-500/30 text-emerald-400'
                              : 'bg-gray-800/30 hover:bg-gray-800/50 text-gray-300 border border-transparent'
                          }
                        `}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">
                              {title.length > 40 ? title.substring(0, 40) + '...' : title}
                            </p>
                            {companyName && (
                              <p className="text-xs text-emerald-400/60 mt-0.5 truncate">
                                {companyName}
                              </p>
                            )}
                            <p className="text-xs text-gray-500 mt-1">
                              {new Date(session.updated_at).toLocaleDateString()}
                            </p>
                          </div>
                          <MessageSquare className="w-4 h-4 text-gray-500 flex-shrink-0 ml-2" />
                        </div>
                      </button>
                    )
                  })}
                </div>
              )}
            </div>
          </div>
        </div>
      )}

      {/* Main Content */}
      <div className="flex-1 flex flex-col">
        {/* Header */}
        <header className="flex items-center justify-between px-6 py-4 border-b border-gray-800/50">
          <div className="flex items-center space-x-4">
            <button
              onClick={() => setShowSidebar(!showSidebar)}
              className="p-2 hover:bg-gray-800/50 rounded-lg transition-all"
            >
              <MessageSquare className="w-5 h-5 text-gray-400" />
            </button>
            <h1 className="text-xl font-bold text-white">Chat</h1>
          </div>

          {/* View Toggle */}
          <div className="flex items-center space-x-2 bg-gray-800/50 rounded-xl p-1">
            <button
              onClick={() => setViewMode('chat')}
              className={`
                flex items-center space-x-2 px-4 py-2 rounded-xl transition-all
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
                flex items-center space-x-2 px-4 py-2 rounded-xl transition-all
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

        {/* Chat Content */}
        <div className="flex-1 overflow-hidden">
          {viewMode === 'chat' ? (
            <ChatView
              companyId={selectedCompany}
              sessionId={sessionId}
              onSessionIdChange={handleSessionUpdate}
            />
          ) : (
            <TreeView
              companyId={selectedCompany}
              sessionId={sessionId}
            />
          )}
        </div>
      </div>
    </div>
  )
}
