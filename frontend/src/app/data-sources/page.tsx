'use client'

import { useState, useEffect } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Upload, Play, Clock, CheckCircle, XCircle, FolderOpen } from 'lucide-react'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'
import { Company } from '@/types/company'
import { CompanySelector } from '@/components/ui/company-selector'

export default function DataSourcesPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const [selectedCompany, setSelectedCompany] = useState<string | null>(
    searchParams.get('company_id')
  )
  const [sources, setSources] = useState<any[]>([])
  const [jobs, setJobs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.push('/sign-in')
    }
  }, [isLoaded, isSignedIn, router])

  useEffect(() => {
    const fetchData = async () => {
      if (!isSignedIn) return
      
      try {
        const token = await getToken()
        const api = createApiClient(token)
        
        const [sourcesData, jobsData] = await Promise.all([
          api.listScrapingSources(),
          api.listScrapingJobs(selectedCompany || undefined),
        ])

        setSources(sourcesData.sources || [])
        setJobs(jobsData.jobs || [])
      } catch (error) {
        console.error('Failed to fetch data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchData()
  }, [getToken, selectedCompany, isSignedIn])

  if (!isLoaded || !isSignedIn || loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950">
        <div className="text-emerald-400 text-lg">Loading...</div>
      </div>
    )
  }

  const getJobStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-5 h-5 text-green-400" />
      case 'running':
      case 'pending':
        return <Clock className="w-5 h-5 text-yellow-400 animate-spin" />
      case 'failed':
        return <XCircle className="w-5 h-5 text-red-400" />
      default:
        return <Clock className="w-5 h-5 text-gray-400" />
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Data Sources</h1>
          <p className="text-white/60">Scrape reviews or import your own data</p>
        </div>

        {/* Company Selector */}
        <div className="mb-8 max-w-md">
          <CompanySelector
            value={selectedCompany}
            onChange={setSelectedCompany}
            placeholder="Select a company..."
          />
        </div>

        {!selectedCompany ? (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="mb-4">
              <FolderOpen className="w-16 h-16 text-emerald-400" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Select a Company</h3>
            <p className="text-white/60 text-center max-w-md">
              Choose a company to start importing or scraping review data
            </p>
          </div>
        ) : (
          <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
            {/* Scraping Sources */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6"
            >
              <h2 className="text-xl font-bold text-white mb-6">Start Scraping</h2>
              
              <div className="space-y-4">
                {sources.length > 0 ? (
                  sources.map((source) => (
                    <div
                      key={source.id}
                      className="p-4 bg-gray-800/50 border border-gray-700/50 rounded-xl hover:border-emerald-500/30 transition-colors"
                    >
                      <div className="flex items-center justify-between mb-2">
                        <h3 className="text-white font-semibold">{source.name}</h3>
                        <span className="text-emerald-400 text-sm">
                          ${source.cost_per_review}/review
                        </span>
                      </div>
                      <p className="text-white/60 text-sm mb-4">{source.description || 'Scrape reviews from this source'}</p>
                      <button className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 rounded-xl text-emerald-400 transition-all duration-200 hover:shadow-lg hover:shadow-emerald-500/20">
                        <Play className="w-4 h-4" />
                        <span>Start Job</span>
                      </button>
                    </div>
                  ))
                ) : (
                  <div className="text-center py-8 text-white/40">
                    No scraping sources configured
                  </div>
                )}
              </div>
            </motion.div>

            {/* CSV Upload */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6"
            >
              <h2 className="text-xl font-bold text-white mb-6">Import Data</h2>
              
              <div className="border-2 border-dashed border-gray-700 rounded-xl p-8 text-center hover:border-emerald-500/50 transition-colors cursor-pointer">
                <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <div className="text-white font-medium mb-2">Upload CSV or JSON</div>
                <div className="text-white/40 text-sm mb-4">
                  Drag and drop or click to browse
                </div>
                <button className="px-6 py-2 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 text-white rounded-xl transition-all duration-200 shadow-lg shadow-emerald-500/20 hover:shadow-xl hover:shadow-emerald-500/30">
                  Browse Files
                </button>
              </div>
            </motion.div>
          </div>
        )}

        {/* Active Jobs */}
        {selectedCompany && jobs.length > 0 && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="mt-8 bg-gray-900/50 border border-gray-800/50 rounded-xl p-6"
          >
            <h2 className="text-xl font-bold text-white mb-6">Recent Jobs</h2>
            
            <div className="space-y-4">
              {jobs.map((job) => (
                <div
                  key={job.id}
                  className="p-4 bg-gray-800/50 border border-gray-700/50 rounded-xl"
                >
                  <div className="flex items-center justify-between mb-3">
                    <div className="flex items-center space-x-3">
                      {getJobStatusIcon(job.status)}
                      <div>
                        <div className="text-white font-medium">{job.source_name || 'Scraping Job'}</div>
                        <div className="text-white/40 text-sm capitalize">{job.status}</div>
                      </div>
                    </div>
                    <div className="text-white/60 text-sm">
                      {job.reviews_fetched}/{job.total_reviews_target} reviews
                    </div>
                  </div>
                  
                  {/* Progress Bar */}
                  <div className="w-full bg-gray-700/30 rounded-full h-2 overflow-hidden">
                    <div
                      className="h-full bg-emerald-500 transition-all duration-300"
                      style={{ width: `${job.progress_percentage}%` }}
                    />
                  </div>
                  
                  <div className="flex items-center justify-between mt-2 text-xs text-white/40">
                    <span>{job.progress_percentage}% complete</span>
                    <span>Cost: ${job.cost}</span>
                  </div>
                </div>
              ))}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}

