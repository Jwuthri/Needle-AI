import { useAuth } from '@clerk/nextjs'
import { useEffect, useRef } from 'react'

export function useUserSync() {
  const { getToken, isSignedIn } = useAuth()
  const syncedRef = useRef(false)

  useEffect(() => {
    const syncUser = async () => {
      if (!isSignedIn || syncedRef.current) {
        return
      }

      try {
        const token = await getToken()
        if (!token) {
          console.log('[UserSync] No token available')
          return
        }

        console.log('[UserSync] Syncing user to database...')
        
        const response = await fetch('http://localhost:8000/api/v1/auth/me', {
          headers: {
            'Authorization': `Bearer ${token}`,
          },
        })

        if (response.ok) {
          const data = await response.json()
          console.log('[UserSync] User synced successfully:', data.email)
          syncedRef.current = true
        } else {
          console.error('[UserSync] Failed to sync user:', response.status)
        }
      } catch (error) {
        console.error('[UserSync] Error syncing user:', error)
      }
    }

    syncUser()
  }, [isSignedIn, getToken])
}

