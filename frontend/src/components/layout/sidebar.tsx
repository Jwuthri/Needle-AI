'use client'

import { usePathname, useRouter } from 'next/navigation'
import Link from 'next/link'
import { UserButton, useAuth } from '@clerk/nextjs'
import {
  Building2,
  MessageSquare,
  BarChart3,
  Database,
  Coins,
  ChevronLeft,
  ChevronRight,
  Plus,
  History,
  MoreVertical,
  Trash2,
  FileText,
  Clock,
} from 'lucide-react'
import { useState, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Logo } from '@/components/ui/logo'
import { createApiClient } from '@/lib/api'
import { ChatSession } from '@/types/chat'

interface SidebarProps {
  conversations?: Array<{
    id: string
    title: string
    lastMessage?: string
  }>
  onNewChat?: () => void
  onSelectSession?: (sessionId: string) => void
  currentSessionId?: string
}

const navItems = [
  { icon: Building2, label: 'Companies', href: '/companies' },
  { icon: MessageSquare, label: 'Chat', href: '/chat' },
  { icon: MessageSquare, label: 'Chat (Experimental)', href: '/chat-experimental', badge: 'NEW' },
  { icon: BarChart3, label: 'Analytics', href: '/analytics' },
  { icon: Database, label: 'Data Sources', href: '/data-sources' },
  { icon: Clock, label: 'Jobs', href: '/jobs' },
  { icon: FileText, label: 'Datasets', href: '/datasets' },
  { icon: Coins, label: 'Credits', href: '/credits' },
]

export function Sidebar({ conversations = [], onNewChat, onSelectSession, currentSessionId }: SidebarProps) {
  const pathname = usePathname()
  const router = useRouter()
  const { getToken } = useAuth()
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const [activeMenu, setActiveMenu] = useState<string | null>(null)
  const [deletingSessionId, setDeletingSessionId] = useState<string | null>(null)
  // Show chat controls for both chat routes
  const isChatRoute = pathname === '/chat' || pathname === '/chat-experimental'

  // Load chat sessions when on chat route
  useEffect(() => {
    const fetchSessions = async () => {
      if (!isChatRoute) return
      
      try {
        const token = await getToken()
        const api = createApiClient(token)
        const sessionsData = await api.listSessions()
        setSessions(sessionsData.sessions || [])
      } catch (error) {
        console.error('Failed to fetch sessions:', error)
      }
    }

    fetchSessions()
    
    // Smart polling: only poll when tab is active (every 30 seconds)
    let interval: NodeJS.Timeout | null = null
    
    const startPolling = () => {
      if (!interval) {
        interval = setInterval(fetchSessions, 30000)
      }
    }
    
    const stopPolling = () => {
      if (interval) {
        clearInterval(interval)
        interval = null
      }
    }
    
    const handleVisibilityChange = () => {
      if (document.visibilityState === 'visible') {
        fetchSessions() // Refresh immediately when tab becomes visible
        startPolling()
      } else {
        stopPolling()
      }
    }
    
    // Start polling if tab is already visible
    if (document.visibilityState === 'visible') {
      startPolling()
    }
    
    document.addEventListener('visibilitychange', handleVisibilityChange)
    
    return () => {
      stopPolling()
      document.removeEventListener('visibilitychange', handleVisibilityChange)
    }
  }, [isChatRoute, getToken])

  const handleNewChat = () => {
    if (onNewChat) {
      onNewChat()
    } else {
      router.push('/chat')
    }
  }

  const handleSessionClick = (sessionId: string) => {
    if (onSelectSession) {
      onSelectSession(sessionId)
    }
  }

  const handleDeleteSession = async (sessionId: string, event: React.MouseEvent) => {
    event.stopPropagation() // Prevent session selection
    
    setDeletingSessionId(sessionId)
    setActiveMenu(null)

    try {
      const token = await getToken()
      const api = createApiClient(token)
      await api.deleteSession(sessionId)
      
      // Remove from local state
      setSessions(sessions.filter(s => s.session_id !== sessionId))
      
      // If deleting current session, navigate to new chat
      if (currentSessionId === sessionId) {
        router.push('/chat')
      }
    } catch (error) {
      console.error('Failed to delete session:', error)
      alert('Failed to delete conversation. Please try again.')
    } finally {
      setDeletingSessionId(null)
    }
  }

  const toggleMenu = (sessionId: string, event: React.MouseEvent) => {
    event.stopPropagation()
    setActiveMenu(activeMenu === sessionId ? null : sessionId)
  }

  // Close menu when clicking outside
  useEffect(() => {
    const handleClickOutside = () => setActiveMenu(null)
    if (activeMenu) {
      document.addEventListener('click', handleClickOutside)
      return () => document.removeEventListener('click', handleClickOutside)
    }
  }, [activeMenu])

  return (
    <motion.aside
      animate={{ width: isCollapsed ? 80 : 280 }}
      className="h-screen bg-gray-900 border-r border-gray-800 flex flex-col relative"
    >
      {/* Logo/Brand */}
      <div className="p-6 border-b border-gray-800">
        <Link href="/dashboard" className="flex items-center justify-center">
          {isCollapsed ? (
            <Logo variant="minimal" className="w-10 h-10" />
          ) : (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
            >
              <Logo className="h-8" />
            </motion.div>
          )}
        </Link>
      </div>

      {/* Collapse Toggle */}
      <button
        onClick={() => setIsCollapsed(!isCollapsed)}
        className="absolute -right-3 top-20 w-6 h-6 bg-gray-800 border border-gray-700 rounded-full flex items-center justify-center text-gray-400 hover:text-emerald-400 hover:border-emerald-500 transition-colors z-10"
      >
        {isCollapsed ? (
          <ChevronRight className="w-4 h-4" />
        ) : (
          <ChevronLeft className="w-4 h-4" />
        )}
      </button>

      {/* Navigation */}
      <nav className="flex-1 p-4 space-y-2 overflow-y-auto">
        {navItems.map((item) => {
          const Icon = item.icon
          // Exact match for chat routes to avoid conflicts between /chat and /chat-experimental
          const isActive = item.href === '/chat' || item.href === '/chat-experimental'
            ? pathname === item.href
            : pathname?.startsWith(item.href)

          return (
            <Link key={item.href} href={item.href}>
              <div
                className={`
                  flex items-center space-x-3 px-4 py-3 rounded-lg transition-all
                  ${
                    isActive
                      ? 'bg-emerald-500/10 text-emerald-400 border border-emerald-500/30'
                      : 'text-gray-400 hover:text-white hover:bg-gray-800/50'
                  }
                `}
              >
                <Icon className="w-5 h-5 flex-shrink-0" />
                {!isCollapsed && (
                  <span className="font-medium flex items-center gap-2">
                    {item.label}
                    {item.badge && (
                      <span className="px-1.5 py-0.5 text-[10px] bg-purple-500/20 text-purple-300 rounded border border-purple-500/30">
                        {item.badge}
                      </span>
                    )}
                  </span>
                )}
              </div>
            </Link>
          )
        })}

        {/* Chat-specific controls */}
        {isChatRoute && !isCollapsed && (
          <div className="mt-6 pt-6 border-t border-gray-800 space-y-4">
            {/* New Chat Button */}
            <button
              onClick={handleNewChat}
              className="w-full flex items-center justify-center space-x-2 px-4 py-3 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 rounded-xl transition-all border border-emerald-500/30"
            >
              <Plus className="w-4 h-4" />
              <span className="font-medium">New Chat</span>
            </button>

            {/* Recent Chats */}
            {sessions.length > 0 && (
              <div>
                <div className="flex items-center space-x-2 px-4 mb-3">
                  <History className="w-4 h-4 text-gray-400" />
                  <h3 className="text-xs text-gray-500 uppercase tracking-wider">Recent Chats</h3>
                </div>
                <div className="space-y-2">
                  {sessions.slice(0, 10).map((session) => {
                    const title = session.metadata?.title || session.messages[0]?.content.substring(0, 40) || 'New Chat'
                    const isActive = currentSessionId === session.session_id
                    const isDeleting = deletingSessionId === session.session_id
                    const menuOpen = activeMenu === session.session_id
                    
                    return (
                      <div key={session.session_id} className="relative">
                        <button
                          onClick={() => handleSessionClick(session.session_id)}
                          disabled={isDeleting}
                          className={`
                            w-full text-left px-3 py-2 rounded-lg transition-all group
                            ${
                              isActive
                                ? 'bg-emerald-500/20 border border-emerald-500/30 text-emerald-400'
                                : 'bg-gray-800/30 hover:bg-gray-800/50 text-gray-300 border border-transparent'
                            }
                            ${isDeleting ? 'opacity-50 cursor-not-allowed' : ''}
                          `}
                        >
                          <div className="flex items-start justify-between gap-2">
                            <div className="flex-1 min-w-0">
                              <p className="text-sm font-medium truncate">
                                {isDeleting ? 'Deleting...' : (title.length > 25 ? title.substring(0, 25) + '...' : title)}
                              </p>
                              <p className="text-xs text-gray-500 mt-1">
                                {new Date(session.updated_at).toLocaleDateString()}
                              </p>
                            </div>
                            <div className="flex items-center gap-1 flex-shrink-0">
                              <MessageSquare className="w-4 h-4 text-gray-500" />
                              {!isDeleting && (
                                <button
                                  onClick={(e) => toggleMenu(session.session_id, e)}
                                  className="opacity-0 group-hover:opacity-100 p-1 hover:bg-gray-700/50 rounded transition-opacity"
                                  aria-label="More options"
                                >
                                  <MoreVertical className="w-4 h-4 text-gray-400" />
                                </button>
                              )}
                            </div>
                          </div>
                        </button>
                        
                        {/* Dropdown Menu */}
                        <AnimatePresence>
                          {menuOpen && (
                            <motion.div
                              initial={{ opacity: 0, scale: 0.95, y: -10 }}
                              animate={{ opacity: 1, scale: 1, y: 0 }}
                              exit={{ opacity: 0, scale: 0.95, y: -10 }}
                              transition={{ duration: 0.1 }}
                              className="absolute right-0 mt-1 w-48 bg-gray-800 border border-gray-700 rounded-lg shadow-lg z-50"
                            >
                              <button
                                onClick={(e) => handleDeleteSession(session.session_id, e)}
                                className="w-full flex items-center gap-2 px-4 py-2 text-sm text-red-400 hover:bg-red-500/10 transition-colors rounded-lg"
                              >
                                <Trash2 className="w-4 h-4" />
                                <span>Delete conversation</span>
                              </button>
                            </motion.div>
                          )}
                        </AnimatePresence>
                      </div>
                    )
                  })}
                </div>
              </div>
            )}
          </div>
        )}
      </nav>

      {/* User Profile */}
      <div className="p-4 border-t border-gray-800">
        <div
          className={`flex items-center ${
            isCollapsed ? 'justify-center' : 'space-x-3'
          }`}
        >
          <UserButton
            appearance={{
              elements: {
                avatarBox: 'w-10 h-10',
              },
            }}
          />
          {!isCollapsed && (
            <div className="flex-1 min-w-0">
              <div className="text-sm text-white font-medium truncate">
                User Profile
              </div>
              <div className="text-xs text-gray-500">Manage account</div>
            </div>
          )}
        </div>
      </div>
    </motion.aside>
  )
}

