'use client'

import { useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { useAuth } from '@clerk/nextjs'

interface RequireAuthProps {
  children: React.ReactNode
  loadingMessage?: string
}

export function RequireAuth({ children, loadingMessage = 'Loading...' }: RequireAuthProps) {
  const router = useRouter()
  const { isLoaded, isSignedIn } = useAuth()

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.push('/sign-in')
    }
  }, [isLoaded, isSignedIn, router])

  if (!isLoaded || !isSignedIn) {
    return (
      <div className="h-screen flex items-center justify-center bg-gray-950">
        <div className="text-gray-400">{loadingMessage}</div>
      </div>
    )
  }

  return <>{children}</>
}

