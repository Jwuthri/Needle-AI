'use client'

import { useState, useRef, useEffect } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { Building2, Check } from 'lucide-react'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'
import { Company } from '@/types/company'

interface CompanySelectorProps {
  value: string | null
  onChange: (companyId: string | null, company?: Company | null) => void
  placeholder?: string
  className?: string
}

export function CompanySelector({ 
  value, 
  onChange, 
  placeholder = 'Select Company',
  className = ''
}: CompanySelectorProps) {
  const { getToken } = useAuth()
  const [companies, setCompanies] = useState<Company[]>([])
  const [showDropdown, setShowDropdown] = useState(false)
  const dropdownRef = useRef<HTMLDivElement>(null)
  
  const selectedCompany = companies.find(c => c.id === value)

  // Load companies
  useEffect(() => {
    const fetchCompanies = async () => {
      try {
        const token = await getToken()
        const api = createApiClient(token)
        const companiesData = await api.listCompanies()
        setCompanies(companiesData.companies || [])
      } catch (error) {
        console.error('Failed to fetch companies:', error)
      }
    }

    fetchCompanies()
  }, [getToken])

  // Close dropdown when clicking outside
  useEffect(() => {
    const handleClickOutside = (event: MouseEvent) => {
      if (dropdownRef.current && !dropdownRef.current.contains(event.target as Node)) {
        setShowDropdown(false)
      }
    }

    document.addEventListener('mousedown', handleClickOutside)
    return () => document.removeEventListener('mousedown', handleClickOutside)
  }, [])

  const handleSelect = (companyId: string | null) => {
    const company = companyId ? companies.find(c => c.id === companyId) : null
    onChange(companyId, company)
    setShowDropdown(false)
  }

  return (
    <div className={`relative ${className}`} ref={dropdownRef}>
      <button
        type="button"
        onClick={() => setShowDropdown(!showDropdown)}
        className="group w-full flex items-center justify-between gap-3 px-4 py-3 bg-gray-800/80 hover:bg-gray-800 border border-gray-700/50 hover:border-emerald-500/50 rounded-xl transition-all shadow-sm"
      >
        <div className="flex items-center gap-3 flex-1 min-w-0">
          <div className="flex-shrink-0 w-10 h-10 rounded-lg bg-emerald-500/10 ring-1 ring-emerald-500/30 flex items-center justify-center group-hover:bg-emerald-500/20 transition-colors">
            <Building2 className="w-5 h-5 text-emerald-400" />
          </div>
          <span className="text-white/90 group-hover:text-white font-medium truncate text-left">
            {selectedCompany ? selectedCompany.name : placeholder}
          </span>
        </div>
        <motion.svg 
          className="w-5 h-5 text-gray-400 group-hover:text-emerald-400 transition-colors flex-shrink-0" 
          fill="none" 
          stroke="currentColor" 
          viewBox="0 0 24 24"
          animate={{ rotate: showDropdown ? 180 : 0 }}
          transition={{ duration: 0.2 }}
        >
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M19 9l-7 7-7-7" />
        </motion.svg>
      </button>

      {/* Dropdown */}
      <AnimatePresence>
        {showDropdown && (
          <>
            {/* Backdrop for mobile */}
            <motion.div 
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              exit={{ opacity: 0 }}
              className="fixed inset-0 z-40 lg:hidden"
              onClick={() => setShowDropdown(false)}
            />
            
            <motion.div
              initial={{ opacity: 0, y: 10, scale: 0.95 }}
              animate={{ opacity: 1, y: 0, scale: 1 }}
              exit={{ opacity: 0, y: 10, scale: 0.95 }}
              transition={{ duration: 0.15 }}
              className="absolute left-0 top-full mt-2 w-full bg-gray-900/95 backdrop-blur-xl border border-gray-700/50 rounded-xl shadow-2xl shadow-black/50 z-50 overflow-hidden"
            >
              {/* Header */}
              <div className="px-4 py-3 border-b border-gray-800/50 bg-gray-800/30">
                <div className="flex items-center justify-between">
                  <div className="flex items-center gap-2">
                    <Building2 className="w-4 h-4 text-emerald-400" />
                    <span className="text-sm font-semibold text-white">Select Company</span>
                  </div>
                  <button
                    type="button"
                    onClick={() => setShowDropdown(false)}
                    className="p-1 hover:bg-gray-700/50 rounded-md transition-colors"
                  >
                    <svg className="w-4 h-4 text-gray-400" fill="none" stroke="currentColor" viewBox="0 0 24 24">
                      <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2} d="M6 18L18 6M6 6l12 12" />
                    </svg>
                  </button>
                </div>
              </div>

              {/* Options List */}
              <div className="max-h-[320px] overflow-y-auto py-2 px-2">
                {/* No Company Option */}
                <button
                  type="button"
                  onClick={() => handleSelect(null)}
                  className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-all group ${
                    !value
                      ? 'bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/40'
                      : 'text-gray-400 hover:text-white hover:bg-gray-800/60'
                  }`}
                >
                  <div className="flex items-center justify-between">
                    <span className="font-medium">All Companies</span>
                    {!value && (
                      <Check className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                    )}
                  </div>
                </button>

                {/* Divider */}
                {companies.length > 0 && (
                  <div className="my-2 px-3">
                    <div className="h-px bg-gray-800/50" />
                  </div>
                )}
                
                {/* Company List */}
                {companies.map((company) => (
                  <button
                    key={company.id}
                    type="button"
                    onClick={() => handleSelect(company.id)}
                    className={`w-full text-left px-3 py-2.5 rounded-lg text-sm transition-all group ${
                      value === company.id
                        ? 'bg-emerald-500/20 text-emerald-400 ring-1 ring-emerald-500/40'
                        : 'text-gray-300 hover:text-white hover:bg-gray-800/60'
                    }`}
                  >
                    <div className="flex items-center justify-between">
                      <div className="flex items-center gap-3 flex-1 min-w-0">
                        <div className={`flex-shrink-0 w-8 h-8 rounded-lg flex items-center justify-center ${
                          value === company.id 
                            ? 'bg-emerald-500/20 ring-1 ring-emerald-500/40' 
                            : 'bg-gray-800/80 group-hover:bg-gray-700/80'
                        }`}>
                          <Building2 className={`w-4 h-4 ${
                            value === company.id ? 'text-emerald-400' : 'text-gray-400 group-hover:text-emerald-400'
                          }`} />
                        </div>
                        <span className="font-medium truncate">{company.name}</span>
                      </div>
                      {value === company.id && (
                        <Check className="w-5 h-5 text-emerald-400 flex-shrink-0" />
                      )}
                    </div>
                  </button>
                ))}
              </div>

              {/* Footer hint */}
              <div className="px-4 py-2 border-t border-gray-800/50 bg-gray-800/20">
                <p className="text-xs text-gray-500">
                  {companies.length === 0 ? 'No companies available' : `${companies.length} ${companies.length === 1 ? 'company' : 'companies'} available`}
                </p>
              </div>
            </motion.div>
          </>
        )}
      </AnimatePresence>
    </div>
  )
}

