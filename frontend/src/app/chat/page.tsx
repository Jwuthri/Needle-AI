'use client'

import { useState, useEffect } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { ChatView } from '@/components/chat/chat-view'
import { useAuth } from '@clerk/nextjs'
import { useChatContext } from '@/components/layout/app-layout'

export default function ChatPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const { isLoaded, isSignedIn } = useAuth()
  const chatContext = useChatContext()
  const [selectedCompany, setSelectedCompany] = useState<string | null>(
    searchParams.get('company_id')
  )

  // Redirect to sign-in if not authenticated
  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.push('/sign-in')
    }
  }, [isLoaded, isSignedIn, router])

  // Show loading state while checking authentication
  if (!isLoaded || !isSignedIn) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-950">
        <div className="text-gray-400">Loading...</div>
      </div>
    )
  }

  return (
    <div className="h-full flex flex-col">
      <ChatView
        companyId={selectedCompany}
        sessionId={chatContext?.currentSessionId}
        onSessionIdChange={chatContext?.setCurrentSessionId}
        onCompanyChange={setSelectedCompany}
      />
    </div>
  )
}
