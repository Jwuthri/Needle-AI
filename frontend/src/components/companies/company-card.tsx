'use client'

import { useState } from 'react'
import { Building2, MoreVertical, Trash2, Edit, ExternalLink, MessageSquare, BarChart3 } from 'lucide-react'
import { useRouter } from 'next/navigation'
import { Company } from '@/types/company'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'

interface CompanyCardProps {
  company: Company
  onUpdate: () => void
}

export function CompanyCard({ company, onUpdate }: CompanyCardProps) {
  const router = useRouter()
  const { getToken } = useAuth()
  const [showMenu, setShowMenu] = useState(false)
  const [deleting, setDeleting] = useState(false)

  const handleDelete = async () => {
    if (!confirm(`Are you sure you want to delete ${company.name}?`)) return

    setDeleting(true)
    try {
      const token = await getToken()
      const api = createApiClient(token)
      await api.deleteCompany(company.id)
      onUpdate()
    } catch (error) {
      console.error('Failed to delete company:', error)
      alert('Failed to delete company')
    } finally {
      setDeleting(false)
      setShowMenu(false)
    }
  }

  return (
    <div className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6 hover:border-emerald-500/30 transition-all group relative">
      {/* Menu */}
      <div className="absolute top-4 right-4">
        <button
          onClick={() => setShowMenu(!showMenu)}
          className="p-2 text-gray-400 hover:text-white transition-colors rounded-xl hover:bg-gray-800/50"
        >
          <MoreVertical className="w-5 h-5" />
        </button>
        {showMenu && (
          <div className="absolute right-0 mt-2 w-48 bg-gray-800 border border-gray-700 rounded-xl shadow-xl z-10">
            <button
              onClick={() => {
                router.push(`/companies/${company.id}`)
                setShowMenu(false)
              }}
              className="w-full flex items-center space-x-2 px-4 py-2 text-white hover:bg-gray-700 transition-colors"
            >
              <Edit className="w-4 h-4" />
              <span>Edit</span>
            </button>
            <button
              onClick={handleDelete}
              disabled={deleting}
              className="w-full flex items-center space-x-2 px-4 py-2 text-red-400 hover:bg-gray-700 transition-colors"
            >
              <Trash2 className="w-4 h-4" />
              <span>{deleting ? 'Deleting...' : 'Delete'}</span>
            </button>
          </div>
        )}
      </div>

      {/* Icon */}
      <div className="w-12 h-12 bg-emerald-500/10 rounded-xl flex items-center justify-center mb-4">
        <Building2 className="w-6 h-6 text-emerald-400" />
      </div>

      {/* Company Info */}
      <h3 className="text-xl font-bold text-white mb-2 group-hover:text-emerald-400 transition-colors">
        {company.name}
      </h3>
      <div className="flex items-center space-x-2 text-white/60 text-sm mb-4">
        <ExternalLink className="w-4 h-4" />
        <span>{company.domain}</span>
      </div>
      <div className="text-white/40 text-sm mb-6">
        {company.industry}
      </div>

      {/* Stats */}
      <div className="grid grid-cols-2 gap-4 mb-6 pb-6 border-b border-gray-800/50">
        <div>
          <div className="text-2xl font-bold text-white">
            {company.total_reviews?.toLocaleString() || 0}
          </div>
          <div className="text-white/40 text-xs">Reviews</div>
        </div>
        <div>
          <div className="text-2xl font-bold text-white">
            {company.last_scrape ? new Date(company.last_scrape).toLocaleDateString() : 'Never'}
          </div>
          <div className="text-white/40 text-xs">Last Scrape</div>
        </div>
      </div>

      {/* Actions */}
      <div className="flex space-x-2">
        <button
          onClick={() => router.push(`/chat?company_id=${company.id}`)}
          className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 rounded-xl text-emerald-400 transition-all duration-200 hover:shadow-lg hover:shadow-emerald-500/20 text-sm"
        >
          <MessageSquare className="w-4 h-4" />
          <span>Chat</span>
        </button>
        <button
          onClick={() => router.push(`/analytics?company_id=${company.id}`)}
          className="flex-1 flex items-center justify-center space-x-2 px-4 py-2 bg-gray-800/50 hover:bg-gray-800 border border-gray-700 rounded-xl text-white transition-colors text-sm"
        >
          <BarChart3 className="w-4 h-4" />
          <span>Analytics</span>
        </button>
      </div>
    </div>
  )
}

