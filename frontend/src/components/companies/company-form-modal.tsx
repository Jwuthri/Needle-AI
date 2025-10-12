'use client'

import { useState } from 'react'
import { X } from 'lucide-react'
import { motion, AnimatePresence } from 'framer-motion'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'

interface CompanyFormModalProps {
  onClose: () => void
  onSuccess: () => void
  initialData?: {
    id?: string
    name: string
    domain: string
    industry: string
  }
}

export function CompanyFormModal({ onClose, onSuccess, initialData }: CompanyFormModalProps) {
  const { getToken } = useAuth()
  const [name, setName] = useState(initialData?.name || '')
  const [domain, setDomain] = useState(initialData?.domain || '')
  const [industry, setIndustry] = useState(initialData?.industry || '')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState('')

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setLoading(true)
    setError('')

    try {
      const token = await getToken()
      const api = createApiClient(token)

      if (initialData?.id) {
        await api.updateCompany(initialData.id, { name, domain, industry })
      } else {
        await api.createCompany({ name, domain, industry })
      }

      onSuccess()
    } catch (err: any) {
      setError(err.message || 'Failed to save company')
    } finally {
      setLoading(false)
    }
  }

  return (
    <AnimatePresence>
      <div className="fixed inset-0 bg-black/60 backdrop-blur-sm flex items-center justify-center z-50 p-4">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="bg-gray-900 border border-gray-800 rounded-xl max-w-md w-full shadow-2xl"
        >
          {/* Header */}
          <div className="flex items-center justify-between p-6 border-b border-gray-800">
            <h2 className="text-2xl font-bold text-white">
              {initialData?.id ? 'Edit Company' : 'Add New Company'}
            </h2>
            <button
              onClick={onClose}
              className="p-2 text-gray-400 hover:text-white transition-colors rounded-lg hover:bg-gray-800/50"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          {/* Form */}
          <form onSubmit={handleSubmit} className="p-6 space-y-4">
            {error && (
              <div className="p-3 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
                {error}
              </div>
            )}

            <div>
              <label className="block text-white text-sm font-medium mb-2">
                Company Name *
              </label>
              <input
                type="text"
                value={name}
                onChange={(e) => setName(e.target.value)}
                required
                placeholder="e.g., Acme Corporation"
                className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
              />
            </div>

            <div>
              <label className="block text-white text-sm font-medium mb-2">
                Domain *
              </label>
              <input
                type="text"
                value={domain}
                onChange={(e) => setDomain(e.target.value)}
                required
                placeholder="e.g., acme.com"
                className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
              />
            </div>

            <div>
              <label className="block text-white text-sm font-medium mb-2">
                Industry *
              </label>
              <input
                type="text"
                value={industry}
                onChange={(e) => setIndustry(e.target.value)}
                required
                placeholder="e.g., SaaS, E-commerce, Healthcare"
                className="w-full px-4 py-3 bg-gray-800/50 border border-gray-700 rounded-lg text-white placeholder-gray-400 focus:outline-none focus:border-emerald-500 focus:ring-1 focus:ring-emerald-500"
              />
            </div>

            {/* Actions */}
            <div className="flex space-x-3 pt-4">
              <button
                type="button"
                onClick={onClose}
                className="flex-1 px-4 py-3 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors"
              >
                Cancel
              </button>
              <button
                type="submit"
                disabled={loading}
                className="flex-1 px-4 py-3 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 disabled:from-gray-600 disabled:to-gray-600 text-white rounded-lg transition-all duration-200"
              >
                {loading ? 'Saving...' : initialData?.id ? 'Update' : 'Create'}
              </button>
            </div>
          </form>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}

