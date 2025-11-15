'use client'

import { useState, useEffect } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { BarChart3, Calendar, Download, TrendingUp, Loader2 } from 'lucide-react'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'
import { CompanySelector } from '@/components/ui/company-selector'
import {
  BarChart,
  Bar,
  LineChart,
  Line,
  PieChart,
  Pie,
  Cell,
  XAxis,
  YAxis,
  CartesianGrid,
  Tooltip,
  Legend,
  ResponsiveContainer
} from 'recharts'

interface AnalyticsData {
  rating_distribution: Array<{ rating: number; count: number }>
  sentiment_trend: Array<{ date: string; sentiment: number; count: number }>
  sentiment_by_source: Array<{ date: string; source: string; sentiment: number; count: number }>
  avg_rating_by_source: Array<{ source: string; avg_rating: number; count: number }>
  source_distribution: Array<{ source: string; count: number }>
  total_reviews: number
  company_name: string | null
  filtered_source: string | null
}

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']

export default function AnalyticsPage() {
  const router = useRouter()
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null)
  const [selectedSource, setSelectedSource] = useState<string | null>(null)
  const [timePeriod, setTimePeriod] = useState<'day' | 'week' | 'month' | 'year'>('month')
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(false)

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.push('/sign-in')
    }
  }, [isLoaded, isSignedIn, router])

  useEffect(() => {
    const fetchAnalytics = async () => {
      if (!selectedCompany || !isSignedIn) {
        setAnalytics(null)
        return
      }

      setLoading(true)
      try {
        const token = await getToken()
        const api = createApiClient(token)
        const data = await api.getUserReviewsStats(
          selectedCompany, 
          selectedSource || undefined, 
          timePeriod
        )
        setAnalytics(data)
      } catch (error) {
        console.error('Failed to fetch analytics:', error)
        setAnalytics(null)
      } finally {
        setLoading(false)
      }
    }

    fetchAnalytics()
  }, [selectedCompany, selectedSource, timePeriod, getToken, isSignedIn])

  if (!isLoaded || !isSignedIn) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950">
        <div className="text-emerald-400 text-lg">Loading...</div>
      </div>
    )
  }

  // Calculate rating stats
  const avgRating = analytics?.rating_distribution.length
    ? (
        analytics.rating_distribution.reduce((sum, item) => sum + item.rating * item.count, 0) /
        analytics.rating_distribution.reduce((sum, item) => sum + item.count, 0)
      ).toFixed(1)
    : '0.0'

  // Calculate sentiment stats from rating
  const positiveCount = analytics?.rating_distribution
    .filter(item => item.rating >= 4)
    .reduce((sum, item) => sum + item.count, 0) || 0
  const neutralCount = analytics?.rating_distribution
    .filter(item => item.rating === 3)
    .reduce((sum, item) => sum + item.count, 0) || 0
  const negativeCount = analytics?.rating_distribution
    .filter(item => item.rating <= 2)
    .reduce((sum, item) => sum + item.count, 0) || 0

  const total = positiveCount + neutralCount + negativeCount || 1
  const positivePercent = ((positiveCount / total) * 100).toFixed(0)
  const neutralPercent = ((neutralCount / total) * 100).toFixed(0)
  const negativePercent = ((negativeCount / total) * 100).toFixed(0)

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

        {/* Company Selector */}
        <div className="mb-8">
          <div className="grid grid-cols-1 md:grid-cols-2 gap-4 max-w-4xl">
            <div>
              <label className="text-sm text-white/60 mb-2 block">Company</label>
              <CompanySelector
                value={selectedCompany}
                onChange={setSelectedCompany}
                placeholder="Select a company to view analytics..."
              />
            </div>
            <div>
              <label className="text-sm text-white/60 mb-2 block">Filter by Source (Optional)</label>
              <select
                value={selectedSource || ''}
                onChange={(e) => setSelectedSource(e.target.value || null)}
                className="w-full px-4 py-2 bg-gray-900/50 border border-gray-800 rounded-xl text-white focus:outline-none focus:ring-2 focus:ring-emerald-500"
                disabled={!analytics}
              >
                <option value="">All Sources</option>
                {analytics?.source_distribution.map((source) => (
                  <option key={source.source} value={source.source}>
                    {source.source} ({source.count})
                  </option>
                ))}
              </select>
            </div>
          </div>
        </div>

        {/* Content */}
        {!selectedCompany ? (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="mb-4">
              <BarChart3 className="w-16 h-16 text-emerald-400" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">Select a Company</h3>
            <p className="text-white/60 text-center max-w-md">
              Choose a company from the dropdown above to view analytics and insights
            </p>
          </div>
        ) : loading ? (
          <div className="flex items-center justify-center py-20">
            <Loader2 className="w-8 h-8 text-emerald-400 animate-spin" />
          </div>
        ) : analytics ? (
          <div>
            {/* Stats Overview */}
            <motion.div
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              className="grid grid-cols-1 md:grid-cols-4 gap-6 mb-8"
            >
              <div className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6">
                <div className="text-3xl font-bold text-white mb-1">
                  {analytics.total_reviews.toLocaleString()}
                </div>
                <div className="text-white/40 text-sm">Total Reviews</div>
              </div>
              <div className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6">
                <div className="text-3xl font-bold text-emerald-400 mb-1">
                  {avgRating} ⭐
                </div>
                <div className="text-white/40 text-sm">Average Rating</div>
              </div>
              <div className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6">
                <div className="text-3xl font-bold text-green-400 mb-1">
                  {positivePercent}%
                </div>
                <div className="text-white/40 text-sm">Positive Reviews</div>
              </div>
              <div className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6">
                <div className="text-3xl font-bold text-red-400 mb-1">
                  {negativePercent}%
                </div>
                <div className="text-white/40 text-sm">Negative Reviews</div>
              </div>
            </motion.div>

            {/* Charts Grid */}
            <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
              {/* Rating Distribution */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.1 }}
                className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6"
              >
                <h3 className="text-xl font-bold text-white mb-6">Rating Distribution</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <BarChart data={analytics.rating_distribution}>
                    <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                    <XAxis 
                      dataKey="rating" 
                      stroke="#9ca3af"
                      label={{ value: 'Rating (Stars)', position: 'insideBottom', offset: -5, fill: '#9ca3af' }}
                    />
                    <YAxis 
                      stroke="#9ca3af"
                      label={{ value: 'Count', angle: -90, position: 'insideLeft', fill: '#9ca3af' }}
                    />
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                      labelStyle={{ color: '#fff' }}
                    />
                    <Bar dataKey="count" fill="#10b981" />
                  </BarChart>
                </ResponsiveContainer>
              </motion.div>

              {/* Source Distribution */}
              <motion.div
                initial={{ opacity: 0, y: 20 }}
                animate={{ opacity: 1, y: 0 }}
                transition={{ delay: 0.2 }}
                className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6"
              >
                <h3 className="text-xl font-bold text-white mb-6">Source Distribution</h3>
                <ResponsiveContainer width="100%" height={300}>
                  <PieChart>
                    <Pie
                      data={analytics.source_distribution}
                      cx="50%"
                      cy="50%"
                      labelLine={false}
                      label={(entry: any) => {
                        const percent = entry.percent || 0
                        return `${entry.name}: ${(percent * 100).toFixed(0)}%`
                      }}
                      outerRadius={100}
                      fill="#8884d8"
                      dataKey="count"
                      nameKey="source"
                    >
                      {analytics.source_distribution.map((entry, index) => (
                        <Cell key={`cell-${index}`} fill={COLORS[index % COLORS.length]} />
                      ))}
                    </Pie>
                    <Tooltip
                      contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                    />
                  </PieChart>
                </ResponsiveContainer>
              </motion.div>

              {/* Sentiment Trend Over Time */}
              {analytics.sentiment_trend.length > 0 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.3 }}
                  className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6 lg:col-span-2"
                >
                  <div className="flex items-center justify-between mb-6">
                    <div className="flex items-center space-x-2">
                      <TrendingUp className="w-5 h-5 text-emerald-400" />
                      <h3 className="text-xl font-bold text-white">Sentiment Trend Over Time</h3>
                    </div>
                    <div className="flex items-center space-x-2">
                      <span className="text-sm text-white/60">Group by:</span>
                      <div className="flex bg-gray-800/50 rounded-lg p-1">
                        {(['day', 'week', 'month', 'year'] as const).map((period) => (
                          <button
                            key={period}
                            onClick={() => setTimePeriod(period)}
                            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${
                              timePeriod === period
                                ? 'bg-emerald-500 text-white'
                                : 'text-white/60 hover:text-white'
                            }`}
                          >
                            {period.charAt(0).toUpperCase() + period.slice(1)}
                          </button>
                        ))}
                      </div>
                    </div>
                  </div>
                  <ResponsiveContainer width="100%" height={300}>
                    <LineChart data={analytics.sentiment_trend}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis 
                        dataKey="date" 
                        stroke="#9ca3af"
                        label={{ 
                          value: timePeriod === 'day' ? 'Day' : timePeriod === 'week' ? 'Week' : timePeriod === 'month' ? 'Month' : 'Year', 
                          position: 'insideBottom', 
                          offset: -5, 
                          fill: '#9ca3af' 
                        }}
                      />
                      <YAxis 
                        stroke="#9ca3af"
                        domain={[-1, 1]}
                        label={{ value: 'Sentiment Score', angle: -90, position: 'insideLeft', fill: '#9ca3af' }}
                      />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                        labelStyle={{ color: '#fff' }}
                      />
                      <Legend />
                      <Line 
                        type="monotone" 
                        dataKey="sentiment" 
                        stroke="#10b981" 
                        strokeWidth={2}
                        dot={{ fill: '#10b981', r: 4 }}
                        activeDot={{ r: 6 }}
                        name="Avg Sentiment"
                      />
                    </LineChart>
                  </ResponsiveContainer>
                </motion.div>
              )}

              {/* Average Rating by Source */}
              {!selectedSource && analytics.avg_rating_by_source.length > 1 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                  className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6 lg:col-span-2"
                >
                  <h3 className="text-xl font-bold text-white mb-6">Average Rating by Source</h3>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart data={analytics.avg_rating_by_source}>
                      <CartesianGrid strokeDasharray="3 3" stroke="#374151" />
                      <XAxis 
                        dataKey="source" 
                        stroke="#9ca3af"
                        angle={-45}
                        textAnchor="end"
                        height={100}
                      />
                      <YAxis 
                        domain={[0, 5]} 
                        stroke="#9ca3af"
                        label={{ value: 'Average Rating', angle: -90, position: 'insideLeft', fill: '#9ca3af' }}
                      />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                        labelStyle={{ color: '#fff' }}
                        formatter={(value: any) => [parseFloat(value).toFixed(2), 'Avg Rating']}
                      />
                      <Bar dataKey="avg_rating" fill="#3b82f6" />
                    </BarChart>
                  </ResponsiveContainer>
                </motion.div>
              )}
            </div>
          </div>
        ) : (
          <div className="flex flex-col items-center justify-center py-20">
            <div className="mb-4">
              <BarChart3 className="w-16 h-16 text-gray-600" />
            </div>
            <h3 className="text-xl font-semibold text-white mb-2">No Data Available</h3>
            <p className="text-white/60 text-center max-w-md">
              No analytics data found for this company. Try generating some reviews first.
            </p>
          </div>
        )}
      </div>
    </div>
  )
}
