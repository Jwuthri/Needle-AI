'use client'

import { ReactNode } from 'react'
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

export function AppLayout({ children, conversations }: AppLayoutProps) {
  const pathname = usePathname()

  // Don't show sidebar on auth pages or landing page
  const noSidebarRoutes = ['/', '/sign-in', '/sign-up']
  const showSidebar = !noSidebarRoutes.some((route) =>
    pathname === route ? true : pathname?.startsWith(route + '/')
  )

  if (!showSidebar) {
    return <>{children}</>
  }

  return (
    <div className="flex h-screen bg-gray-950 overflow-hidden">
      <Sidebar conversations={conversations} />
      <main className="flex-1 overflow-auto">{children}</main>
    </div>
  )
}

