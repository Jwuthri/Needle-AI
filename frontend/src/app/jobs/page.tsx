'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Clock, CheckCircle, XCircle, Loader2, AlertCircle, RefreshCw } from 'lucide-react'
import { useAuth } from '@clerk/nextjs'
import { useJobPolling } from '@/hooks/use-job-polling'
import { CompanySelector } from '@/components/ui/company-selector'

export default function JobsPage() {
  const router = useRouter()
  const { isLoaded, isSignedIn } = useAuth()
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null)

  // Use job polling hook
  const { jobs, loading, error, refetch } = useJobPolling({
    companyId: selectedCompany || undefined,
    enabled: isSignedIn && isLoaded,
  })

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.push('/sign-in')
    }
  }, [isLoaded, isSignedIn, router])

  if (!isLoaded || !isSignedIn) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950">
        <Loader2 className="w-8 h-8 text-emerald-400 animate-spin" />
      </div>
    )
  }

  const getStatusBadge = (status: string) => {
    const styles = {
      pending: 'bg-yellow-500/10 border-yellow-500/30 text-yellow-400',
      running: 'bg-blue-500/10 border-blue-500/30 text-blue-400',
      completed: 'bg-green-500/10 border-green-500/30 text-green-400',
      failed: 'bg-red-500/10 border-red-500/30 text-red-400',
      cancelled: 'bg-gray-500/10 border-gray-500/30 text-gray-400',
    }

    const icons = {
      pending: <Clock className="w-4 h-4" />,
      running: <Loader2 className="w-4 h-4 animate-spin" />,
      completed: <CheckCircle className="w-4 h-4" />,
      failed: <XCircle className="w-4 h-4" />,
      cancelled: <XCircle className="w-4 h-4" />,
    }

    return (
      <div className={`flex items-center gap-2 px-3 py-1 rounded-full border text-sm font-medium ${styles[status as keyof typeof styles] || styles.pending}`}>
        {icons[status as keyof typeof icons] || icons.pending}
        <span className="capitalize">{status}</span>
      </div>
    )
  }

  const formatDate = (dateString: string | null) => {
    if (!dateString) return 'N/A'
    const date = new Date(dateString)
    return date.toLocaleString('en-US', {
      month: 'short',
      day: 'numeric',
      hour: '2-digit',
      minute: '2-digit',
    })
  }

  const calculateDuration = (startedAt: string | null, completedAt: string | null) => {
    if (!startedAt) return 'N/A'
    const start = new Date(startedAt).getTime()
    const end = completedAt ? new Date(completedAt).getTime() : Date.now()
    const durationMs = end - start

    // Handle negative durations (timezone issues or job hasn't truly started)
    if (durationMs < 0) return '0s'

    const seconds = Math.floor(durationMs / 1000)
    const minutes = Math.floor(seconds / 60)

    if (minutes > 0) {
      return `${minutes}m ${seconds % 60}s`
    }
    return `${seconds}s`
  }

  return (
    <div className="min-h-screen bg-gray-950 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Jobs</h1>
          <p className="text-white/60">Monitor your review scraping and generation jobs</p>
        </div>

        {/* Filters */}
        <div className="mb-6 flex flex-col sm:flex-row gap-4">
          {/* Company Selector */}
          <div className="flex-1 max-w-md">
            <CompanySelector
              value={selectedCompany}
              onChange={setSelectedCompany}
              placeholder="Select a company..."
            />
          </div>

          {/* Refresh Button */}
          {/* <button
            onClick={() => refetch()}
            disabled={loading}
            className="flex items-center gap-2 px-4 py-2 bg-gray-800 hover:bg-gray-700 border border-gray-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed h-16"
          >
            <RefreshCw className={`w-4 h-4 ${loading ? 'animate-spin' : ''}`} />
            <span>Refresh</span>
          </button> */}
        </div>

        {/* Error State */}
        {error && (
          <motion.div
            initial={{ opacity: 0, y: -10 }}
            animate={{ opacity: 1, y: 0 }}
            className="mb-6 p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center gap-3"
          >
            <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
            <div className="text-red-400 text-sm">{error}</div>
          </motion.div>
        )}

        {/* Loading State */}
        {loading && jobs.length === 0 && (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-emerald-400 animate-spin" />
          </div>
        )}

        {/* Empty State */}
        {!loading && jobs.length === 0 && (
          <div className="flex flex-col items-center justify-center py-20">
            <Clock className="w-16 h-16 text-gray-600 mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">No Jobs Found</h3>
            <p className="text-white/60 text-center max-w-md">
              {!selectedCompany
                ? 'Select a company to view its jobs, or view all jobs by selecting "All Companies"'
                : 'No jobs have been created yet for this company. Start by creating a new job from the data sources page.'}
            </p>
            <button
              onClick={() => router.push('/data-sources')}
              className="mt-6 px-6 py-2 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 text-white rounded-xl transition-all duration-200 shadow-lg shadow-emerald-500/20"
            >
              Go to Data Sources
            </button>
          </div>
        )}

        {/* Jobs List */}
        {jobs.length > 0 && (
          <div className="space-y-4">
            {jobs.map((job) => (
              <motion.div
                key={job.id}
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6 hover:border-emerald-500/30 transition-colors"
              >
                <div className="flex flex-col lg:flex-row lg:items-center justify-between gap-4 mb-4">
                  <div className="flex-1">
                    <div className="flex items-center gap-3 mb-2">
                      <h3 className="text-lg font-semibold text-white">
                        {job.source_name || 'Reviews'}: {job.company_name || `Company ${job.company_id.slice(0, 8)}`}
                      </h3>
                      {getStatusBadge(job.status)}
                    </div>
                    <div className="flex flex-wrap gap-4 text-sm text-white/60">
                      <span className="text-white/40">#{job.id.slice(0, 8)}</span>
                      <span>Created: {formatDate(job.created_at)}</span>
                      {job.started_at && (
                        <span>Duration: {calculateDuration(job.started_at, job.completed_at)}</span>
                      )}
                      <span className="text-emerald-400">Cost: ${job.cost.toFixed(2)}</span>
                    </div>
                  </div>
                  <div className="text-right">
                    <div className="text-2xl font-bold text-white mb-1">
                      {job.reviews_fetched}/{job.total_reviews_target}
                    </div>
                    <div className="text-sm text-white/60">reviews</div>
                  </div>
                </div>

                {/* Progress Bar */}
                <div className="mb-3">
                  <div className="flex items-center justify-between mb-2">
                    <span className="text-sm text-white/60">Progress</span>
                    <span className="text-sm font-medium text-white">
                      {job.progress_percentage.toFixed(1)}%
                    </span>
                  </div>
                  <div className="w-full bg-gray-700/30 rounded-full h-3 overflow-hidden">
                    <motion.div
                      initial={{ width: 0 }}
                      animate={{ width: `${job.progress_percentage}%` }}
                      transition={{ duration: 0.5 }}
                      className={`h-full transition-all duration-300 ${job.status === 'completed'
                        ? 'bg-gradient-to-r from-green-500 to-emerald-500'
                        : job.status === 'failed'
                          ? 'bg-red-500'
                          : 'bg-gradient-to-r from-blue-500 to-cyan-500'
                        }`}
                    />
                  </div>
                </div>

                {/* Error Message */}
                {job.error_message && (
                  <div className="mt-3 p-3 bg-red-500/10 border border-red-500/30 rounded-lg">
                    <div className="flex items-start gap-2">
                      <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0 mt-0.5" />
                      <div>
                        <div className="text-red-400 font-medium text-sm mb-1">Error</div>
                        <div className="text-red-400/80 text-sm">{job.error_message}</div>
                      </div>
                    </div>
                  </div>
                )}
              </motion.div>
            ))}
          </div>
        )}
      </div>
    </div>
  )
}

