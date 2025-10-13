'use client'

import { ReactNode, createContext, useContext, useState } from 'react'
import { Sidebar } from './sidebar'
import { usePathname } from 'next/navigation'

interface AppLayoutProps {
  children: ReactNode
  conversations?: Array<{
    id: string
    title: string
    lastMessage?: string
  }>
}

interface ChatContextType {
  currentSessionId?: string
  setCurrentSessionId: (id: string | undefined) => void
  handleNewChat: () => void
  handleSelectSession: (sessionId: string) => void
}

const ChatContext = createContext<ChatContextType | null>(null)

export function useChatContext() {
  return useContext(ChatContext)
}

export function AppLayout({ children, conversations }: AppLayoutProps) {
  const pathname = usePathname()
  const [currentSessionId, setCurrentSessionId] = useState<string>()

  // Don't show sidebar on auth pages or landing page
  const noSidebarRoutes = ['/', '/sign-in', '/sign-up']
  const showSidebar = !noSidebarRoutes.some((route) =>
    pathname === route ? true : pathname?.startsWith(route + '/')
  )

  const handleNewChat = () => {
    setCurrentSessionId(undefined)
  }

  const handleSelectSession = (sessionId: string) => {
    setCurrentSessionId(sessionId)
  }

  if (!showSidebar) {
    return <>{children}</>
  }

  return (
    <ChatContext.Provider
      value={{
        currentSessionId,
        setCurrentSessionId,
        handleNewChat,
        handleSelectSession,
      }}
    >
      <div className="flex h-screen bg-gray-950 overflow-hidden">
        <Sidebar
          conversations={conversations}
          onNewChat={handleNewChat}
          onSelectSession={handleSelectSession}
          currentSessionId={currentSessionId}
        />
        <main className="flex-1 overflow-auto">{children}</main>
      </div>
    </ChatContext.Provider>
  )
}

