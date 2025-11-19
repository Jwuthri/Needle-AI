'use client'

import { useEffect, useState } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Building2, MessageSquare, Database, TrendingUp, Plus, Activity } from 'lucide-react'
import Link from 'next/link'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'
import { useUserSync } from '@/hooks/use-user-sync'

export default function DashboardPage() {
  const router = useRouter()
  const { isLoaded, isSignedIn, getToken } = useAuth()
  
  // Redirect to sign-in if not authenticated
  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.push('/sign-in')
    }
  }, [isLoaded, isSignedIn, router])
  
  // Sync user to database when they land on dashboard
  useUserSync()
  
  const [stats, setStats] = useState({
    totalCompanies: 0,
    totalReviews: 0,
    creditsRemaining: 0,
    activeJobs: 0,
  })
  const [recentActivity, setRecentActivity] = useState<any[]>([])
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    const fetchDashboardData = async () => {
      if (!isSignedIn) return
      
      try {
        const token = await getToken()
        const api = createApiClient(token)

        // Fetch companies
        const companiesData = await api.listCompanies()
        const totalCompanies = companiesData.companies?.length || 0

        // Fetch credits
        const creditsData = await api.getCreditBalance()
        const creditsRemaining = creditsData.credits_available || 0

        // Fetch scraping jobs
        const jobsData = await api.listScrapingJobs()
        const activeJobs = jobsData.jobs?.filter((j: any) => j.status === 'running' || j.status === 'pending').length || 0

        // Calculate total reviews (mock for now)
        const totalReviews = companiesData.companies?.reduce((sum: number, c: any) => sum + (c.total_reviews || 0), 0) || 0

        setStats({
          totalCompanies,
          totalReviews,
          creditsRemaining,
          activeJobs,
        })

        // Mock recent activity
        setRecentActivity([
          { id: 1, type: 'scraping', message: 'Completed scraping 500 Reddit reviews', time: '2 hours ago' },
          { id: 2, type: 'chat', message: 'New chat session started', time: '3 hours ago' },
          { id: 3, type: 'company', message: 'Added new company: Acme Corp', time: '1 day ago' },
        ])
      } catch (error) {
        console.error('Failed to fetch dashboard data:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchDashboardData()
  }, [getToken, isSignedIn])

  // Show loading state while checking authentication or loading data
  if (!isLoaded || !isSignedIn || loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950">
        <div className="text-emerald-400 text-lg">Loading dashboard...</div>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Dashboard</h1>
          <p className="text-white/60">Welcome back! Here's your overview.</p>
        </div>

        {/* Stats Cards */}
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-6 mb-8">
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6 hover:border-emerald-500/30 transition-colors"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-emerald-500/10 rounded-xl flex items-center justify-center">
                <Building2 className="w-6 h-6 text-emerald-400" />
              </div>
              <div className="text-2xl font-bold text-white">{stats.totalCompanies}</div>
            </div>
            <div className="text-white/60 text-sm">Companies</div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.2 }}
            className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6 hover:border-emerald-500/30 transition-colors"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-blue-500/10 rounded-xl flex items-center justify-center">
                <MessageSquare className="w-6 h-6 text-blue-400" />
              </div>
              <div className="text-2xl font-bold text-white">{stats.totalReviews.toLocaleString()}</div>
            </div>
            <div className="text-white/60 text-sm">Total Reviews</div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.3 }}
            className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6 hover:border-emerald-500/30 transition-colors"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-purple-500/10 rounded-xl flex items-center justify-center">
                <TrendingUp className="w-6 h-6 text-purple-400" />
              </div>
              <div className="text-2xl font-bold text-white">{stats.creditsRemaining.toLocaleString()}</div>
            </div>
            <div className="text-white/60 text-sm">Credits Remaining</div>
          </motion.div>

          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.4 }}
            className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6 hover:border-emerald-500/30 transition-colors"
          >
            <div className="flex items-center justify-between mb-4">
              <div className="w-12 h-12 bg-orange-500/10 rounded-xl flex items-center justify-center">
                <Activity className="w-6 h-6 text-orange-400" />
              </div>
              <div className="text-2xl font-bold text-white">{stats.activeJobs}</div>
            </div>
            <div className="text-white/60 text-sm">Active Jobs</div>
          </motion.div>
        </div>

        <div className="grid grid-cols-1 lg:grid-cols-2 gap-8">
          {/* Quick Actions */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.5 }}
            className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6"
          >
            <h2 className="text-xl font-bold text-white mb-6">Quick Actions</h2>
            <div className="space-y-3">
              <Link href="/companies">
                <button className="w-full flex items-center space-x-3 px-4 py-3 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 rounded-xl text-emerald-400 transition-all duration-200 hover:shadow-lg hover:shadow-emerald-500/20">
                  <Plus className="w-5 h-5" />
                  <span className="font-medium">Add New Company</span>
                </button>
              </Link>
              <Link href="/chat-experimental">
                <button className="w-full flex items-center space-x-3 px-4 py-3 bg-gray-800/50 hover:bg-gray-800 border border-gray-700 rounded-xl text-white transition-colors">
                  <MessageSquare className="w-5 h-5" />
                  <span className="font-medium">Start Chat Session</span>
                </button>
              </Link>
              <Link href="/data-sources">
                <button className="w-full flex items-center space-x-3 px-4 py-3 bg-gray-800/50 hover:bg-gray-800 border border-gray-700 rounded-xl text-white transition-colors">
                  <Database className="w-5 h-5" />
                  <span className="font-medium">Import Data</span>
                </button>
              </Link>
            </div>
          </motion.div>

          {/* Recent Activity */}
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.6 }}
            className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6"
          >
            <h2 className="text-xl font-bold text-white mb-6">Recent Activity</h2>
            <div className="space-y-4">
              {recentActivity.length > 0 ? (
                recentActivity.map((activity) => (
                  <div key={activity.id} className="flex items-start space-x-3 pb-4 border-b border-gray-800/50 last:border-0">
                    <div className="w-8 h-8 bg-emerald-500/10 rounded-xl flex items-center justify-center flex-shrink-0">
                      <Activity className="w-4 h-4 text-emerald-400" />
                    </div>
                    <div className="flex-1 min-w-0">
                      <div className="text-white text-sm">{activity.message}</div>
                      <div className="text-white/40 text-xs mt-1">{activity.time}</div>
                    </div>
                  </div>
                ))
              ) : (
                <div className="text-white/40 text-sm text-center py-8">No recent activity</div>
              )}
            </div>
          </motion.div>
        </div>
      </div>
    </div>
  )
}

