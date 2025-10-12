'use client'

import { usePathname } from 'next/navigation'
import Link from 'next/link'
import { UserButton } from '@clerk/nextjs'
import {
  Building2,
  MessageSquare,
  BarChart3,
  Database,
  Coins,
  ChevronLeft,
  ChevronRight,
} from 'lucide-react'
import { useState } from 'react'
import { motion, AnimatePresence } from 'framer-motion'

interface SidebarProps {
  conversations?: Array<{
    id: string
    title: string
    lastMessage?: string
  }>
}

const navItems = [
  { icon: Building2, label: 'Companies', href: '/companies' },
  { icon: MessageSquare, label: 'Chat', href: '/chat' },
  { icon: BarChart3, label: 'Analytics', href: '/analytics' },
  { icon: Database, label: 'Data Sources', href: '/data-sources' },
  { icon: Coins, label: 'Credits', href: '/credits' },
]

export function Sidebar({ conversations = [] }: SidebarProps) {
  const pathname = usePathname()
  const [isCollapsed, setIsCollapsed] = useState(false)
  const isChatRoute = pathname?.startsWith('/chat')

  return (
    <motion.aside
      animate={{ width: isCollapsed ? 80 : 280 }}
      className="h-screen bg-gray-900 border-r border-gray-800 flex flex-col relative"
    >
      {/* Logo/Brand */}
      <div className="p-6 border-b border-gray-800">
        <Link href="/dashboard" className="flex items-center space-x-3">
          <div className="w-10 h-10 bg-gradient-to-br from-emerald-500 to-green-600 rounded-lg flex items-center justify-center">
            <span className="text-white font-bold text-xl">N</span>
          </div>
          {!isCollapsed && (
            <motion.span
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="text-white font-bold text-lg tracking-wide"
            >
              NeedleAI
            </motion.span>
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

        {/* Conversations List (only on chat route) */}
        {isChatRoute && !isCollapsed && conversations.length > 0 && (
          <div className="mt-6 pt-6 border-t border-gray-800">
            <div className="text-xs text-gray-500 uppercase tracking-wider px-4 mb-2">
              Recent Chats
            </div>
            <div className="space-y-1">
              {conversations.slice(0, 5).map((conv) => (
                <Link key={conv.id} href={`/chat/${conv.id}`}>
                  <div className="px-4 py-2 rounded-lg text-sm text-gray-400 hover:text-white hover:bg-gray-800/50 transition-colors truncate">
                    {conv.title || 'Untitled conversation'}
                  </div>
                </Link>
              ))}
            </div>
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

