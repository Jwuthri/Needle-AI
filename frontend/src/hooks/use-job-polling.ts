import { useState, useEffect, useCallback, useRef } from 'react'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'

interface Job {
  id: string
  company_id: string
  source_id: string
  user_id: string
  status: 'pending' | 'running' | 'completed' | 'failed' | 'cancelled'
  progress_percentage: number
  total_reviews_target: number
  reviews_fetched: number
  cost: number
  celery_task_id: string | null
  error_message: string | null
  created_at: string
  started_at: string | null
  completed_at: string | null
}

interface UseJobPollingOptions {
  jobId?: string
  companyId?: string
  enabled?: boolean
  pollInterval?: number
}

interface UseJobPollingReturn {
  jobs: Job[]
  loading: boolean
  error: string | null
  refetch: () => Promise<void>
}

/**
 * Custom hook for polling job status with real-time updates
 * 
 * @param options Configuration options
 * @returns Job data, loading state, error, and refetch function
 */
export function useJobPolling({
  jobId,
  companyId,
  enabled = true,
  pollInterval = 2500, // Poll every 2.5 seconds by default
}: UseJobPollingOptions = {}): UseJobPollingReturn {
  const { getToken } = useAuth()
  const [jobs, setJobs] = useState<Job[]>([])
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string | null>(null)
  const pollTimeoutRef = useRef<NodeJS.Timeout | null>(null)
  const isMountedRef = useRef(true)

  const fetchJobs = useCallback(async () => {
    if (!enabled) return

    try {
      const token = await getToken()
      const api = createApiClient(token)

      if (jobId) {
        // Fetch single job
        const job = await api.getScrapingJob(jobId)
        if (isMountedRef.current) {
          setJobs([job])
          setError(null)
        }
      } else {
        // Fetch list of jobs
        const result = await api.listScrapingJobs(companyId)
        if (isMountedRef.current) {
          setJobs(result.jobs || result)
          setError(null)
        }
      }
    } catch (err: any) {
      console.error('Error fetching jobs:', err)
      if (isMountedRef.current) {
        setError(err.message || 'Failed to fetch jobs')
      }
    } finally {
      if (isMountedRef.current) {
        setLoading(false)
      }
    }
  }, [jobId, companyId, enabled, getToken])

  const scheduleNextPoll = useCallback(() => {
    if (!enabled || !isMountedRef.current) return

    // Check if any jobs are still running
    const hasRunningJobs = jobs.some(
      job => job.status === 'pending' || job.status === 'running'
    )

    if (hasRunningJobs) {
      pollTimeoutRef.current = setTimeout(() => {
        fetchJobs().then(() => scheduleNextPoll())
      }, pollInterval)
    }
  }, [jobs, enabled, fetchJobs, pollInterval])

  // Initial fetch
  useEffect(() => {
    isMountedRef.current = true
    fetchJobs()

    return () => {
      isMountedRef.current = false
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current)
      }
    }
  }, [fetchJobs])

  // Set up polling for running jobs
  useEffect(() => {
    if (pollTimeoutRef.current) {
      clearTimeout(pollTimeoutRef.current)
    }

    scheduleNextPoll()

    return () => {
      if (pollTimeoutRef.current) {
        clearTimeout(pollTimeoutRef.current)
      }
    }
  }, [scheduleNextPoll])

  const refetch = useCallback(async () => {
    setLoading(true)
    await fetchJobs()
  }, [fetchJobs])

  return {
    jobs,
    loading,
    error,
    refetch,
  }
}

