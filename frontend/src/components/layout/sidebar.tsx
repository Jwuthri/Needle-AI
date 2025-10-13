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
  { icon: BarChart3, label: 'Analytics', href: '/analytics' },
  { icon: Database, label: 'Data Sources', href: '/data-sources' },
  { icon: Coins, label: 'Credits', href: '/credits' },
]

export function Sidebar({ conversations = [], onNewChat, onSelectSession, currentSessionId }: SidebarProps) {
  const pathname = usePathname()
  const router = useRouter()
  const { getToken } = useAuth()
  const [isCollapsed, setIsCollapsed] = useState(false)
  const [sessions, setSessions] = useState<ChatSession[]>([])
  const isChatRoute = pathname?.startsWith('/chat')

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
    
    // Refresh sessions every 10 seconds when on chat route
    const interval = setInterval(fetchSessions, 10000)
    return () => clearInterval(interval)
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
          const isActive = pathname?.startsWith(item.href)

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
                  <span className="font-medium">{item.label}</span>
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
                    
                    return (
                      <button
                        key={session.session_id}
                        onClick={() => handleSessionClick(session.session_id)}
                        className={`
                          w-full text-left px-3 py-2 rounded-lg transition-all
                          ${
                            isActive
                              ? 'bg-emerald-500/20 border border-emerald-500/30 text-emerald-400'
                              : 'bg-gray-800/30 hover:bg-gray-800/50 text-gray-300 border border-transparent'
                          }
                        `}
                      >
                        <div className="flex items-start justify-between">
                          <div className="flex-1 min-w-0">
                            <p className="text-sm font-medium truncate">
                              {title.length > 30 ? title.substring(0, 30) + '...' : title}
                            </p>
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

