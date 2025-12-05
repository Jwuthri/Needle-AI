'use client'

import { useState, useEffect } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { useAuth } from '@clerk/nextjs'
import { useChatContext } from '@/components/layout/app-layout'
import { ExperimentalChatView } from '@/components/chat/experimental-chat-view'

export default function ChatExperimentalPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const { isLoaded, isSignedIn } = useAuth()
  const chatContext = useChatContext()
  const [selectedCompany, setSelectedCompany] = useState<string | null>(
    searchParams.get('company_id')
  )
  const [selectedDataset, setSelectedDataset] = useState<string | null>(
    searchParams.get('dataset_id')
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
      <ExperimentalChatView
        companyId={selectedCompany}
        sessionId={chatContext?.currentSessionId}
        onSessionIdChange={chatContext?.setCurrentSessionId}
        onCompanyChange={setSelectedCompany}
        datasetId={selectedDataset}
        onDatasetChange={setSelectedDataset}
      />
    </div>
  )
}

