'use client'

import { useState, useEffect } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Table, BarChart3, Calendar, Download } from 'lucide-react'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'
import { Company } from '@/types/company'

type ViewMode = 'table' | 'graph'

export default function AnalyticsPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const [viewMode, setViewMode] = useState<ViewMode>('table')
  const [selectedCompany, setSelectedCompany] = useState<string | null>(
    searchParams.get('company_id')
  )
  const [companies, setCompanies] = useState<Company[]>([])
  const [analytics, setAnalytics] = useState<any>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.push('/sign-in')
    }
  }, [isLoaded, isSignedIn, router])

  useEffect(() => {
    const fetchCompanies = async () => {
      if (!isSignedIn) return
      
      try {
        const token = await getToken()
        const api = createApiClient(token)
        const data = await api.listCompanies()
        setCompanies(data.companies || [])
      } catch (error) {
        console.error('Failed to fetch companies:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchCompanies()
  }, [getToken, isSignedIn])

  useEffect(() => {
    const fetchAnalytics = async () => {
      if (!selectedCompany || !isSignedIn) return

      setLoading(true)
      try {
        const token = await getToken()
        const api = createApiClient(token)
        const data = await api.getAnalyticsOverview(selectedCompany)
        setAnalytics(data)
      } catch (error) {
        console.error('Failed to fetch analytics:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchAnalytics()
  }, [selectedCompany, getToken, isSignedIn])

  if (!isLoaded || !isSignedIn) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950">
        <div className="text-emerald-400 text-lg">Loading...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="flex items-center justify-between mb-8">
          <div>
            <h1 className="text-4xl font-bold text-white mb-2">Analytics</h1>
            <p className="text-white/60">Explore insights and trends from your review data</p>
          </div>

          <div className="flex items-center space-x-4">
            <button className="flex items-center space-x-2 px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-xl text-white hover:bg-gray-800 transition-colors">
              <Calendar className="w-4 h-4" />
              <span>Date Range</span>
            </button>
            <button className="flex items-center space-x-2 px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-xl text-white hover:bg-gray-800 transition-colors">
              <Download className="w-4 h-4" />
              <span>Export</span>
            </button>
          </div>
        </div>

        {/* Company Selector & View Toggle */}
        <div className="flex items-center justify-between mb-8">
          <select
            value={selectedCompany || ''}
            onChange={(e) => setSelectedCompany(e.target.value || null)}
            className="px-4 py-2 bg-gray-800/50 border border-gray-700 rounded-xl text-white focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
          >
            <option value="">Select a company...</option>
            {companies.map((company) => (
              <option key={company.id} value={company.id}>
                {company.name}
              </option>
            ))}
          </select>

          <div className="flex items-center space-x-2 bg-gray-800/50 rounded-xl p-1">
            <button
              onClick={() => setViewMode('table')}
              className={`flex items-center space-x-2 px-4 py-2 rounded-xl transition-all ${
                viewMode === 'table'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <Table className="w-4 h-4" />
              <span className="font-medium">Table</span>
            </button>
            <button
              onClick={() => setViewMode('graph')}
              className={`flex items-center space-x-2 px-4 py-2 rounded-xl transition-all ${
                viewMode === 'graph'
                  ? 'bg-emerald-500/20 text-emerald-400 border border-emerald-500/30'
                  : 'text-gray-400 hover:text-white'
              }`}
            >
              <BarChart3 className="w-4 h-4" />
              <span className="font-medium">Graph</span>
            </button>
          </div>
        </div>

        {/* Content */}
        {!selectedCompany ? (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="text-6xl mb-4">📊</div>
            <h3 className="text-xl font-semibold text-white mb-2">Select a Company</h3>
            <p className="text-white/60 text-center max-w-md">
              Choose a company from the dropdown above to view analytics and insights
            </p>
          </div>
        ) : loading ? (
          <div className="flex items-center justify-center py-20">
            <div className="text-emerald-400 text-lg">Loading analytics...</div>
          </div>
        ) : (
          <div>
            {/* Stats Overview */}
            {analytics && (
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8"
              >
                <div className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6">
                  <div className="text-3xl font-bold text-white mb-1">
                    {analytics.total_reviews?.toLocaleString() || 0}
                  </div>
                  <div className="text-white/40 text-sm">Total Reviews</div>
                </div>
                <div className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6">
                  <div className="text-3xl font-bold text-green-400 mb-1">
                    {analytics.sentiment_distribution?.positive || 0}%
                  </div>
                  <div className="text-white/40 text-sm">Positive</div>
                </div>
                <div className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6">
                  <div className="text-3xl font-bold text-yellow-400 mb-1">
                    {analytics.sentiment_distribution?.neutral || 0}%
                  </div>
                  <div className="text-white/40 text-sm">Neutral</div>
                </div>
                <div className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6">
                  <div className="text-3xl font-bold text-red-400 mb-1">
                    {analytics.sentiment_distribution?.negative || 0}%
                  </div>
                  <div className="text-white/40 text-sm">Negative</div>
                </div>
              </motion.div>
            )}

            {/* Data View */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: 0.1 }}
              className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-8"
            >
              {viewMode === 'table' ? (
                <div>
                  <h3 className="text-xl font-bold text-white mb-6">Reviews Data</h3>
                  <div className="overflow-x-auto">
                    <table className="w-full">
                      <thead>
                        <tr className="border-b border-gray-800">
                          <th className="text-left py-3 px-4 text-white/60 text-sm font-medium">Author</th>
                          <th className="text-left py-3 px-4 text-white/60 text-sm font-medium">Content</th>
                          <th className="text-left py-3 px-4 text-white/60 text-sm font-medium">Source</th>
                          <th className="text-left py-3 px-4 text-white/60 text-sm font-medium">Sentiment</th>
                          <th className="text-left py-3 px-4 text-white/60 text-sm font-medium">Date</th>
                        </tr>
                      </thead>
                      <tbody>
                        <tr>
                          <td colSpan={5} className="text-center py-12 text-white/40">
                            No review data available yet
                          </td>
                        </tr>
                      </tbody>
                    </table>
                  </div>
                </div>
              ) : (
                <div>
                  <h3 className="text-xl font-bold text-white mb-6">Sentiment Trends</h3>
                  <div className="h-96 flex items-center justify-center text-white/40">
                    Chart visualization will be displayed here
                  </div>
                </div>
              )}
            </motion.div>
          </div>
        )}
      </div>
    </div>
  )
}

