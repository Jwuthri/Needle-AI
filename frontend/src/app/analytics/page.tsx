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

interface BoxPlotData {
  source: string
  min: number
  q1: number
  median: number
  q3: number
  max: number
  mean: number
  outliers: number[]
  count: number
}

interface AnalyticsData {
  rating_distribution: Array<{ rating: number; count: number }>
  sentiment_trend: Array<{ date: string; sentiment: number; count: number }>
  sentiment_by_source: Array<{ date: string; source: string; sentiment: number; count: number }>
  avg_rating_by_source: BoxPlotData[]
  source_distribution: Array<{ source: string; count: number }>
  total_reviews: number
  company_name: string | null
  filtered_source: string | null
}

const COLORS = ['#10b981', '#3b82f6', '#f59e0b', '#ef4444', '#8b5cf6']

// Custom BoxPlot component for Recharts
const BoxPlot = ({ x, y, width, height, data }: any) => {
  const boxWidth = Math.min(width * 0.6, 40)
  const centerX = x + width / 2
  const scale = height / 5 // Scale for 0-5 rating range

  const minY = y + height - (data.min * scale)
  const q1Y = y + height - (data.q1 * scale)
  const medianY = y + height - (data.median * scale)
  const q3Y = y + height - (data.q3 * scale)
  const maxY = y + height - (data.max * scale)
  const meanY = y + height - (data.mean * scale)

  return (
    <g>
      {/* Whiskers */}
      <line x1={centerX} y1={minY} x2={centerX} y2={q1Y} stroke="#9ca3af" strokeWidth={2} />
      <line x1={centerX} y1={q3Y} x2={centerX} y2={maxY} stroke="#9ca3af" strokeWidth={2} />

      {/* Min/Max caps */}
      <line x1={centerX - boxWidth / 4} y1={minY} x2={centerX + boxWidth / 4} y2={minY} stroke="#9ca3af" strokeWidth={2} />
      <line x1={centerX - boxWidth / 4} y1={maxY} x2={centerX + boxWidth / 4} y2={maxY} stroke="#9ca3af" strokeWidth={2} />

      {/* Box (IQR) */}
      <rect
        x={centerX - boxWidth / 2}
        y={q3Y}
        width={boxWidth}
        height={q1Y - q3Y}
        fill="#3b82f6"
        fillOpacity={0.7}
        stroke="#3b82f6"
        strokeWidth={2}
      />

      {/* Median line */}
      <line
        x1={centerX - boxWidth / 2}
        y1={medianY}
        x2={centerX + boxWidth / 2}
        y2={medianY}
        stroke="#fff"
        strokeWidth={3}
      />

      {/* Mean point */}
      <circle cx={centerX} cy={meanY} r={4} fill="#10b981" stroke="#fff" strokeWidth={2} />

      {/* Outliers */}
      {data.outliers && data.outliers.map((outlier: number, idx: number) => {
        const outlierY = y + height - (outlier * scale)
        return (
          <circle
            key={idx}
            cx={centerX}
            cy={outlierY}
            r={3}
            fill="#ef4444"
            fillOpacity={0.6}
          />
        )
      })}
    </g>
  )
}

export default function AnalyticsPage() {
  const router = useRouter()
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const [selectedCompany, setSelectedCompany] = useState<string | null>(null)
  const [selectedSource, setSelectedSource] = useState<string | null>(null)
  const [timePeriod, setTimePeriod] = useState<'day' | 'week' | 'month' | 'year'>('month')
  const [analytics, setAnalytics] = useState<AnalyticsData | null>(null)
  const [loading, setLoading] = useState(false)
  const [trendLoading, setTrendLoading] = useState(false)

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

      // Only show full loading when company/source changes
      const isCompanyOrSourceChange = !analytics ||
        analytics.company_name !== selectedCompany ||
        analytics.filtered_source !== selectedSource

      if (isCompanyOrSourceChange) {
        setLoading(true)
      } else {
        // Only trend data is changing (time period)
        setTrendLoading(true)
      }

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
        if (isCompanyOrSourceChange) {
          setAnalytics(null)
        }
      } finally {
        setLoading(false)
        setTrendLoading(false)
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
              {/* <label className="text-sm text-white/60 mb-2 block">Company</label> */}
              <CompanySelector
                value={selectedCompany}
                onChange={setSelectedCompany}
                placeholder="Select a company..."
              />
            </div>
            <div>
              {/* <label className="text-sm text-white/60 mb-2 block">Filter by Source (Optional)</label> */}
              <div className="relative">
                <div className="absolute left-4 top-1/2 -translate-y-1/2 flex-shrink-0 w-10 h-10 rounded-lg bg-emerald-500/10 ring-1 ring-emerald-500/30 flex items-center justify-center pointer-events-none">
                  <BarChart3 className="w-5 h-5 text-emerald-400" />
                </div>
                <select
                  value={selectedSource || ''}
                  onChange={(e) => setSelectedSource(e.target.value || null)}
                  className="w-full h-16 pl-[4.25rem] pr-12 bg-gray-800/80 hover:bg-gray-800 border border-gray-700/50 hover:border-emerald-500/50 rounded-xl text-white/90 hover:text-white font-medium focus:outline-none focus:ring-2 focus:ring-emerald-500 transition-all shadow-sm disabled:opacity-50 disabled:cursor-not-allowed appearance-none"
                  disabled={!analytics}
                >
                  <option value="">All Sources</option>
                  {analytics?.source_distribution.map((source) => (
                    <option key={source.source} value={source.source}>
                      {source.source} ({source.count})
                    </option>
                  ))}
                </select>
                <div className="absolute right-4 top-1/2 -translate-y-1/2 pointer-events-none">
                  <svg className="w-5 h-5 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                    <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
                  </svg>
                </div>
              </div>
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
                            disabled={trendLoading}
                            className={`px-3 py-1 rounded text-sm font-medium transition-colors ${timePeriod === period
                              ? 'bg-emerald-500 text-white'
                              : 'text-white/60 hover:text-white'
                              } ${trendLoading ? 'opacity-50 cursor-not-allowed' : ''}`}
                          >
                            {period.charAt(0).toUpperCase() + period.slice(1)}
                          </button>
                        ))}
                      </div>
                      {trendLoading && (
                        <Loader2 className="w-4 h-4 text-emerald-400 animate-spin" />
                      )}
                    </div>
                  </div>
                  <div className="relative">
                    {trendLoading && (
                      <div className="absolute inset-0 bg-gray-900/50 backdrop-blur-sm flex items-center justify-center z-10 rounded-lg">
                        <Loader2 className="w-6 h-6 text-emerald-400 animate-spin" />
                      </div>
                    )}
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
                  </div>
                </motion.div>
              )}

              {/* Average Rating by Source - BoxPlot */}
              {!selectedSource && analytics.avg_rating_by_source.length > 1 && (
                <motion.div
                  initial={{ opacity: 0, y: 20 }}
                  animate={{ opacity: 1, y: 0 }}
                  transition={{ delay: 0.4 }}
                  className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6 lg:col-span-2"
                >
                  <div className="mb-6">
                    <h3 className="text-xl font-bold text-white mb-2">Rating Distribution by Source</h3>
                    <div className="flex items-center space-x-4 text-sm text-white/60">
                      <div className="flex items-center space-x-1">
                        <div className="w-3 h-3 rounded-full bg-blue-500"></div>
                        <span>Box (Q1-Q3)</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <div className="w-3 h-0.5 bg-white"></div>
                        <span>Median</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <div className="w-3 h-3 rounded-full bg-emerald-500"></div>
                        <span>Mean</span>
                      </div>
                      <div className="flex items-center space-x-1">
                        <div className="w-3 h-3 rounded-full bg-red-500/60"></div>
                        <span>Outliers</span>
                      </div>
                    </div>
                  </div>
                  <ResponsiveContainer width="100%" height={300}>
                    <BarChart
                      data={analytics.avg_rating_by_source}
                      margin={{ top: 20, right: 30, left: 20, bottom: 80 }}
                    >
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
                        label={{ value: 'Rating', angle: -90, position: 'insideLeft', fill: '#9ca3af' }}
                      />
                      <Tooltip
                        contentStyle={{ backgroundColor: '#1f2937', border: '1px solid #374151', borderRadius: '8px' }}
                        labelStyle={{ color: '#fff' }}
                        content={({ active, payload }) => {
                          if (active && payload && payload.length) {
                            const data = payload[0].payload
                            return (
                              <div className="bg-gray-800 border border-gray-700 rounded-lg p-3">
                                <p className="text-white font-semibold mb-2">{data.source}</p>
                                <p className="text-emerald-400 text-sm">Mean: {data.mean.toFixed(2)}</p>
                                <p className="text-white text-sm">Median: {data.median.toFixed(2)}</p>
                                <p className="text-white/60 text-sm">Q3: {data.q3.toFixed(2)}</p>
                                <p className="text-white/60 text-sm">Q1: {data.q1.toFixed(2)}</p>
                                <p className="text-white/40 text-sm">Range: {data.min.toFixed(1)} - {data.max.toFixed(1)}</p>
                                <p className="text-white/40 text-sm">Count: {data.count}</p>
                                {data.outliers && data.outliers.length > 0 && (
                                  <p className="text-red-400 text-sm">Outliers: {data.outliers.length}</p>
                                )}
                              </div>
                            )
                          }
                          return null
                        }}
                      />
                      <Bar
                        dataKey="median"
                        shape={(props: any) => <BoxPlot {...props} data={props.payload} />}
                      />
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
