'use client'

import { useEffect, useState } from 'react'
import { useParams, useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { ArrowLeft, Edit, Trash2, ExternalLink, MessageSquare, BarChart3, Database } from 'lucide-react'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'
import { Company } from '@/types/company'
import { CompanyFormModal } from '@/components/companies/company-form-modal'

export default function CompanyDetailPage() {
  const params = useParams()
  const router = useRouter()
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const [company, setCompany] = useState<Company | null>(null)
  const [loading, setLoading] = useState(true)
  const [showEditModal, setShowEditModal] = useState(false)
  const companyId = params.id as string

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.push('/sign-in')
    }
  }, [isLoaded, isSignedIn, router])

  const fetchCompany = async () => {
    if (!isSignedIn) return
    
    try {
      const token = await getToken()
      const api = createApiClient(token)
      const data = await api.getCompany(companyId)
      setCompany(data)
    } catch (error) {
      console.error('Failed to fetch company:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    if (companyId && isSignedIn) {
      fetchCompany()
    }
  }, [companyId, getToken, isSignedIn])

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete ${company?.name}?`)) return

    try {
      const token = await getToken()
      const api = createApiClient(token)
      await api.deleteCompany(companyId)
      router.push('/companies')
    } catch (error) {
      console.error('Failed to delete company:', error)
      alert('Failed to delete company')
    }
  }

  if (!isLoaded || !isSignedIn || loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950">
        <div className="text-emerald-400 text-lg">Loading company...</div>
      </div>
    )
  }

  if (!company) {
    return (
      <div className="flex flex-col items-center justify-center h-screen bg-gray-950">
        <div className="text-white text-xl mb-4">Company not found</div>
        <button
          onClick={() => router.push('/companies')}
          className="text-emerald-400 hover:text-emerald-300"
        >
          Go back to companies
        </button>
      </div>
    )
  }

  return (
    <div className="min-h-screen bg-gray-950 p-8">
      <div className="max-w-5xl mx-auto">
        {/* Back Button */}
        <button
          onClick={() => router.push('/companies')}
          className="flex items-center space-x-2 text-white/60 hover:text-white mb-6 transition-colors"
        >
          <ArrowLeft className="w-5 h-5" />
          <span>Back to Companies</span>
        </button>

        {/* Company Header */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-8 mb-8"
        >
          <div className="flex items-start justify-between mb-6">
            <div className="flex items-start space-x-4">
              <div className="w-16 h-16 bg-emerald-500/10 rounded-xl flex items-center justify-center">
                <ExternalLink className="w-8 h-8 text-emerald-400" />
              </div>
              <div>
                <h1 className="text-3xl font-bold text-white mb-2">{company.name}</h1>
                <a
                  href={`https://${company.domain}`}
                  target="_blank"
                  rel="noopener noreferrer"
                  className="text-emerald-400 hover:text-emerald-300 transition-colors flex items-center space-x-2"
                >
                  <span>{company.domain}</span>
                  <ExternalLink className="w-4 h-4" />
                </a>
                <div className="text-white/60 mt-2">{company.industry}</div>
              </div>
            </div>
            <div className="flex space-x-2">
              <button
                onClick={() => setShowEditModal(true)}
                className="p-3 bg-gray-800/50 hover:bg-gray-800 border border-gray-700 rounded-lg text-white transition-colors"
              >
                <Edit className="w-5 h-5" />
              </button>
              <button
                onClick={handleDelete}
                className="p-3 bg-red-500/10 hover:bg-red-500/20 border border-red-500/30 rounded-lg text-red-400 transition-colors"
              >
                <Trash2 className="w-5 h-5" />
              </button>
            </div>
          </div>

          {/* Stats */}
          <div className="grid grid-cols-3 gap-6">
            <div className="bg-gray-800/30 rounded-lg p-4">
              <div className="text-3xl font-bold text-white mb-1">
                {company.total_reviews?.toLocaleString() || 0}
              </div>
              <div className="text-white/40 text-sm">Total Reviews</div>
            </div>
            <div className="bg-gray-800/30 rounded-lg p-4">
              <div className="text-3xl font-bold text-white mb-1">
                {company.last_scrape ? new Date(company.last_scrape).toLocaleDateString() : 'Never'}
              </div>
              <div className="text-white/40 text-sm">Last Scrape</div>
            </div>
            <div className="bg-gray-800/30 rounded-lg p-4">
              <div className="text-3xl font-bold text-white mb-1">
                {new Date(company.created_at).toLocaleDateString()}
              </div>
              <div className="text-white/40 text-sm">Created</div>
            </div>
          </div>
        </motion.div>

        {/* Quick Actions */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.1 }}
          className="grid grid-cols-3 gap-6 mb-8"
        >
          <button
            onClick={() => router.push(`/chat?company_id=${companyId}`)}
            className="flex flex-col items-center p-6 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 rounded-xl text-emerald-400 transition-all group"
          >
            <MessageSquare className="w-10 h-10 mb-3 group-hover:scale-110 transition-transform" />
            <span className="font-medium">Start Chat</span>
            <span className="text-xs text-emerald-400/60 mt-1">Ask questions about reviews</span>
          </button>

          <button
            onClick={() => router.push(`/analytics?company_id=${companyId}`)}
            className="flex flex-col items-center p-6 bg-gray-800/50 hover:bg-gray-800 border border-gray-700 rounded-xl text-white transition-all group"
          >
            <BarChart3 className="w-10 h-10 mb-3 group-hover:scale-110 transition-transform" />
            <span className="font-medium">View Analytics</span>
            <span className="text-xs text-white/40 mt-1">Explore data and insights</span>
          </button>

          <button
            onClick={() => router.push(`/data-sources?company_id=${companyId}`)}
            className="flex flex-col items-center p-6 bg-gray-800/50 hover:bg-gray-800 border border-gray-700 rounded-xl text-white transition-all group"
          >
            <Database className="w-10 h-10 mb-3 group-hover:scale-110 transition-transform" />
            <span className="font-medium">Import Data</span>
            <span className="text-xs text-white/40 mt-1">Scrape or upload reviews</span>
          </button>
        </motion.div>

        {/* Recent Activity Placeholder */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: 0.2 }}
          className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-8"
        >
          <h2 className="text-xl font-bold text-white mb-6">Recent Activity</h2>
          <div className="text-white/40 text-center py-8">
            No recent activity for this company
          </div>
        </motion.div>
      </div>

      {/* Edit Modal */}
      {showEditModal && (
        <CompanyFormModal
          initialData={{
            id: companyId,
            name: company.name,
            domain: company.domain,
            industry: company.industry,
          }}
          onClose={() => setShowEditModal(false)}
          onSuccess={() => {
            setShowEditModal(false)
            fetchCompany()
          }}
        />
      )}
    </div>
  )
}

