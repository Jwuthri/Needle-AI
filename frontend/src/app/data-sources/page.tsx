'use client'

import { useState, useEffect, useRef } from 'react'
import { useSearchParams, useRouter } from 'next/navigation'
import { motion, AnimatePresence } from 'framer-motion'
import { Upload, Play, Clock, CheckCircle, XCircle, FolderOpen, Loader2, AlertCircle, X, DollarSign, Hash } from 'lucide-react'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'
import { Company } from '@/types/company'
import { CompanySelector } from '@/components/ui/company-selector'

interface JobStartDialogProps {
  isOpen: boolean
  onClose: () => void
  source: any
  companyId: string
  companyData?: any  // Company object with review_urls
  onJobStarted: () => void
}

function JobStartDialog({ isOpen, onClose, source, companyId, companyData, onJobStarted }: JobStartDialogProps) {
  const { getToken } = useAuth()
  const [inputMode, setInputMode] = useState<'count' | 'cost'>('count')
  const [reviewCount, setReviewCount] = useState<string>('10')
  const [maxCost, setMaxCost] = useState<string>('1.00')
  const [customUrl, setCustomUrl] = useState<string>('')
  const [starting, setStarting] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const [creditBalance, setCreditBalance] = useState<number>(0)
  
  // Check if this is a real scraper (not fake)
  const isRealScraper = !(
    source.config?.type === 'fake_generator' ||
    source.name?.toLowerCase().includes('fake') ||
    source.name?.toLowerCase().includes('llm')
  )
  
  // Get discovered URL for this source type
  const getDiscoveredUrl = () => {
    if (!companyData?.review_urls) return ''
    const sourceType = source.source_type?.toLowerCase()
    return companyData.review_urls[sourceType] || ''
  }

  // Pre-fill URL from discovered URLs when dialog opens
  useEffect(() => {
    if (isOpen && isRealScraper) {
      const discoveredUrl = getDiscoveredUrl()
      if (discoveredUrl && !customUrl) {
        setCustomUrl(discoveredUrl)
      }
    }
  }, [isOpen, source.source_type, companyData])

  useEffect(() => {
    if (isOpen) {
      // Fetch credit balance
      const fetchCredits = async () => {
        try {
          const token = await getToken()
          const api = createApiClient(token)
          const balance = await api.getCreditBalance()
          setCreditBalance(balance.credits_available || 0)
        } catch (err) {
          console.error('Error fetching credits:', err)
        }
      }
      fetchCredits()
    }
  }, [isOpen, getToken])

  const calculateEstimate = () => {
    if (inputMode === 'count') {
      const count = parseInt(reviewCount) || 0
      const cost = count * source.cost_per_review
      return { reviews: count, cost: cost.toFixed(2) }
    } else {
      const cost = parseFloat(maxCost) || 0
      const reviews = Math.floor(cost / source.cost_per_review)
      return { reviews, cost: cost.toFixed(2) }
    }
  }

  const handleStartJob = async () => {
    const estimate = calculateEstimate()
    const costNum = parseFloat(estimate.cost)

    console.log('Source object:', source)
    console.log('Source ID:', source.id)
    console.log('Company ID:', companyId)

    if (costNum > creditBalance) {
      setError(`Insufficient credits. Required: $${estimate.cost}, Available: $${creditBalance.toFixed(2)}`)
      return
    }

    if (estimate.reviews < 1) {
      setError('Must generate at least 1 review')
      return
    }

    setStarting(true)
    setError(null)

    try {
      const token = await getToken()
      const api = createApiClient(token)
      
      // Build request payload
      const payload: any = {
        company_id: companyId,
        source_id: source.id,
        generation_mode: isRealScraper ? 'real' : 'fake'
      }
      
      if (inputMode === 'count') {
        payload.review_count = estimate.reviews
      } else {
        payload.max_cost = costNum
      }
      
      // Add custom URL/query for real scrapers
      if (isRealScraper && customUrl.trim()) {
        payload.query = customUrl.trim()
      }
      
      console.log('Starting job with payload:', payload)
      
      await api.startScrapingJob(payload)

      onJobStarted()
      onClose()
    } catch (err: any) {
      console.error('Job start error:', err)
      setError(err.message || 'Failed to start job')
    } finally {
      setStarting(false)
    }
  }

  const estimate = calculateEstimate()

  if (!isOpen) return null

  return (
    <AnimatePresence>
      <div className="fixed inset-0 z-50 flex items-center justify-center bg-black/60 backdrop-blur-sm">
        <motion.div
          initial={{ opacity: 0, scale: 0.95 }}
          animate={{ opacity: 1, scale: 1 }}
          exit={{ opacity: 0, scale: 0.95 }}
          className="bg-gray-900 border border-gray-800 rounded-xl p-6 w-full max-w-md mx-4 shadow-2xl"
        >
          <div className="flex items-center justify-between mb-4">
            <h2 className="text-xl font-bold text-white">
              {isRealScraper ? 'Start Review Scraping' : 'Start Review Generation'}
            </h2>
            <button
              onClick={onClose}
              className="text-gray-400 hover:text-white transition-colors"
            >
              <X className="w-5 h-5" />
            </button>
          </div>

          <div className="space-y-4">
            <div>
              <div className="text-sm text-white/60 mb-1">Source</div>
              <div className="text-white font-medium">{source.name}</div>
              <div className="text-emerald-400 text-sm">${source.cost_per_review}/review</div>
            </div>

            {/* Input Mode Toggle */}
            <div className="flex gap-2">
              <button
                onClick={() => setInputMode('count')}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg transition-all ${
                  inputMode === 'count'
                    ? 'bg-emerald-500/20 border-2 border-emerald-500 text-emerald-400'
                    : 'bg-gray-800 border-2 border-gray-700 text-gray-400 hover:border-gray-600'
                }`}
              >
                <Hash className="w-4 h-4" />
                <span className="font-medium">Number of Reviews</span>
              </button>
              <button
                onClick={() => setInputMode('cost')}
                className={`flex-1 flex items-center justify-center gap-2 px-4 py-2 rounded-lg transition-all ${
                  inputMode === 'cost'
                    ? 'bg-emerald-500/20 border-2 border-emerald-500 text-emerald-400'
                    : 'bg-gray-800 border-2 border-gray-700 text-gray-400 hover:border-gray-600'
                }`}
              >
                <DollarSign className="w-4 h-4" />
                <span className="font-medium">Maximum Cost</span>
              </button>
            </div>

            {/* Input Field */}
            {inputMode === 'count' ? (
              <div>
                <label className="block text-sm font-medium text-white/80 mb-2">
                  Number of Reviews
                </label>
                <input
                  type="number"
                  min="1"
                  max="1000"
                  value={reviewCount}
                  onChange={(e) => setReviewCount(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500 transition-colors"
                  placeholder="e.g., 10"
                />
              </div>
            ) : (
              <div>
                <label className="block text-sm font-medium text-white/80 mb-2">
                  Maximum Cost ($)
                </label>
                <input
                  type="number"
                  min="0.01"
                  max="1000"
                  step="0.01"
                  value={maxCost}
                  onChange={(e) => setMaxCost(e.target.value)}
                  className="w-full px-4 py-2 bg-gray-800 border border-gray-700 rounded-lg text-white focus:outline-none focus:border-emerald-500 transition-colors"
                  placeholder="e.g., 5.00"
                />
              </div>
            )}

            {/* Custom URL for real scrapers */}
            {isRealScraper && (
              <div>
                <div className="flex items-center justify-between mb-2">
                  <label className="text-sm font-medium text-white/80">
                    Product URL
                  </label>
                  {getDiscoveredUrl() && (
                    <span className="text-xs text-emerald-400 flex items-center gap-1">
                      <svg className="w-3 h-3" fill="currentColor" viewBox="0 0 20 20">
                        <path fillRule="evenodd" d="M10 18a8 8 0 100-16 8 8 0 000 16zm3.707-9.293a1 1 0 00-1.414-1.414L9 10.586 7.707 9.293a1 1 0 00-1.414 1.414l2 2a1 1 0 001.414 0l4-4z" clipRule="evenodd" />
                      </svg>
                      Auto-discovered
                    </span>
                  )}
                </div>
                <input
                  type="text"
                  value={customUrl}
                  onChange={(e) => setCustomUrl(e.target.value)}
                  className={`w-full px-4 py-2 bg-gray-800 border rounded-lg text-white focus:outline-none focus:border-emerald-500 transition-colors text-sm ${
                    getDiscoveredUrl() && customUrl === getDiscoveredUrl() 
                      ? 'border-emerald-500/50' 
                      : 'border-gray-700'
                  }`}
                  placeholder={
                    source.source_type === 'g2' 
                      ? 'e.g., https://www.g2.com/products/notion/reviews or just "notion"'
                      : source.source_type === 'trustpilot'
                      ? 'e.g., https://www.trustpilot.com/review/notion.so'
                      : source.source_type === 'trustradius'
                      ? 'e.g., https://www.trustradius.com/products/slack/reviews'
                      : 'Product name or review page URL'
                  }
                />
                <p className="text-xs text-white/40 mt-1">
                  {getDiscoveredUrl() 
                    ? 'URL auto-discovered from web search. Edit if needed.' 
                    : 'Enter the product name or full review page URL. Leave empty to use company name.'}
                </p>
              </div>
            )}

            {/* Estimate */}
            <div className="bg-gray-800/50 border border-gray-700/50 rounded-lg p-4">
              <div className="text-sm text-white/60 mb-2">Estimate</div>
              <div className="flex items-center justify-between">
                <span className="text-white">Reviews:</span>
                <span className="text-white font-bold">{estimate.reviews}</span>
              </div>
              <div className="flex items-center justify-between mt-1">
                <span className="text-white">Total Cost:</span>
                <span className="text-emerald-400 font-bold">${estimate.cost}</span>
              </div>
              <div className="flex items-center justify-between mt-2 pt-2 border-t border-gray-700">
                <span className="text-white/60 text-sm">Available Credits:</span>
                <span className={`font-bold text-sm ${creditBalance >= parseFloat(estimate.cost) ? 'text-green-400' : 'text-red-400'}`}>
                  ${creditBalance.toFixed(2)}
                </span>
              </div>
            </div>

            {/* Error Message */}
            {error && (
              <div className="bg-red-500/10 border border-red-500/30 rounded-lg p-3 flex items-center gap-2">
                <AlertCircle className="w-4 h-4 text-red-400 flex-shrink-0" />
                <span className="text-red-400 text-sm">{error}</span>
              </div>
            )}

            {/* Action Buttons */}
            <div className="flex gap-3 pt-2">
              <button
                onClick={onClose}
                disabled={starting}
                className="flex-1 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-lg transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
              >
                Cancel
              </button>
              <button
                onClick={handleStartJob}
                disabled={starting}
                className="flex-1 px-4 py-2 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 text-white rounded-lg transition-all duration-200 shadow-lg shadow-emerald-500/20 disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center gap-2"
              >
                {starting ? (
                  <>
                    <Loader2 className="w-4 h-4 animate-spin" />
                    Starting...
                  </>
                ) : (
                  <>
                    <Play className="w-4 h-4" />
                    Start Job
                  </>
                )}
              </button>
            </div>
          </div>
        </motion.div>
      </div>
    </AnimatePresence>
  )
}

export default function DataSourcesPage() {
  const searchParams = useSearchParams()
  const router = useRouter()
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const [selectedCompanyId, setSelectedCompanyId] = useState<string | null>(
    searchParams.get('company_id')
  )
  const [selectedCompanyData, setSelectedCompanyData] = useState<any>(null)
  const [sources, setSources] = useState<any[]>([])
  const [jobs, setJobs] = useState<any[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null)
  const [tableName, setTableName] = useState('')
  const [dragActive, setDragActive] = useState(false)
  const [jobDialogOpen, setJobDialogOpen] = useState(false)
  const [selectedSource, setSelectedSource] = useState<any>(null)
  const fileInputRef = useRef<HTMLInputElement>(null)
  
  // Handle company selection
  const handleCompanyChange = (companyId: string | null, company?: any) => {
    setSelectedCompanyId(companyId)
    setSelectedCompanyData(company || null)
  }

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.push('/sign-in')
    }
  }, [isLoaded, isSignedIn, router])

  const fetchData = async () => {
    if (!isSignedIn) return
    
    try {
      const token = await getToken()
      const api = createApiClient(token)
      
      const [sourcesData, jobsData] = await Promise.all([
        api.listScrapingSources(),
        api.listScrapingJobs(selectedCompanyId || undefined),
      ])

      // Combine real and fake sources
      const allSources = [
        ...(sourcesData.real_sources || []),
        ...(sourcesData.fake_sources || [])
      ]
      setSources(allSources)
      setJobs(jobsData.jobs || jobsData)
    } catch (error) {
      console.error('Failed to fetch data:', error)
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    fetchData()
  }, [selectedCompanyId, isSignedIn])

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

  const handleStartJob = (source: any) => {
    setSelectedSource(source)
    setJobDialogOpen(true)
  }

  const handleJobStarted = () => {
    fetchData()
    router.push('/jobs')
  }

  const handleFileSelect = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setUploadError('Only CSV files are supported')
      setTimeout(() => setUploadError(null), 5000)
      return
    }

    const nameToUse = tableName.trim() || file.name.replace(/\.csv$/i, '').replace(/[^a-zA-Z0-9_]/g, '_')

    if (!nameToUse) {
      setUploadError('Please enter a table name')
      setTimeout(() => setUploadError(null), 5000)
      return
    }

    setUploading(true)
    setUploadError(null)
    setUploadSuccess(null)

    try {
      const token = await getToken()
      const api = createApiClient(token)
      const response = await api.uploadUserDataset(file, nameToUse)

      setUploadSuccess(`Successfully uploaded ${response.row_count} rows!`)
      setTableName('')
      
      setTimeout(() => setUploadSuccess(null), 5000)
      setTimeout(() => {
        router.push('/datasets')
      }, 2000)
    } catch (error: any) {
      let errorMessage = error.message || 'Failed to upload CSV'
      
      if (error.status === 409 || (error.message && error.message.toLowerCase().includes('already exists'))) {
        errorMessage = `A dataset with this name already exists. Please choose a different name.`
      }
      
      setUploadError(errorMessage)
      setTimeout(() => setUploadError(null), 8000)
    } finally {
      setUploading(false)
    }
  }

  const handleDrag = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    if (e.type === 'dragenter' || e.type === 'dragover') {
      setDragActive(true)
    } else if (e.type === 'dragleave') {
      setDragActive(false)
    }
  }

  const handleDrop = (e: React.DragEvent) => {
    e.preventDefault()
    e.stopPropagation()
    setDragActive(false)

    if (e.dataTransfer.files && e.dataTransfer.files[0]) {
      handleFileSelect(e.dataTransfer.files[0])
    }
  }

  const handleFileInputChange = (e: React.ChangeEvent<HTMLInputElement>) => {
    if (e.target.files && e.target.files[0]) {
      handleFileSelect(e.target.files[0])
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
            value={selectedCompanyId}
            onChange={handleCompanyChange}
            placeholder="Select a company..."
          />
        </div>

        {!selectedCompanyId ? (
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
                      <button 
                        onClick={() => handleStartJob(source)}
                        className="w-full flex items-center justify-center space-x-2 px-4 py-2 bg-emerald-500/10 hover:bg-emerald-500/20 border border-emerald-500/30 rounded-xl text-emerald-400 transition-all duration-200 hover:shadow-lg hover:shadow-emerald-500/20"
                      >
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

              
              {/* Table Name Input */}
              <div className="mb-4">
                <label className="block text-sm font-medium text-white/80 mb-2">
                  Table Name (optional)
                </label>
                <input
                  type="text"
                  value={tableName}
                  onChange={(e) => setTableName(e.target.value)}
                  placeholder="e.g., products, sales (auto-generated from filename if empty)"
                  className="w-full px-4 py-2 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-white/40 focus:outline-none focus:border-emerald-500/50 transition-colors"
                  disabled={uploading}
                />
              </div>

              <input
                ref={fileInputRef}
                type="file"
                accept=".csv"
                onChange={handleFileInputChange}
                className="hidden"
                disabled={uploading}
              />
              
              <div
                onDragEnter={handleDrag}
                onDragLeave={handleDrag}
                onDragOver={handleDrag}
                onDrop={handleDrop}
                onClick={() => !uploading && fileInputRef.current?.click()}
                className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors cursor-pointer ${
                  dragActive
                    ? 'border-emerald-500 bg-emerald-500/10'
                    : 'border-gray-700 hover:border-emerald-500/50'
                } ${uploading ? 'cursor-not-allowed opacity-50' : ''}`}
              >
                {uploading ? (
                  <>
                    <Loader2 className="w-12 h-12 text-emerald-400 animate-spin mx-auto mb-4" />
                    <div className="text-white font-medium">Uploading and processing...</div>
                    <div className="text-white/40 text-sm mt-2">This may take a moment</div>
                  </>
                ) : (
                  <>
                    <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                    <div className="text-white font-medium mb-2">Upload CSV File</div>
                    <div className="text-white/40 text-sm mb-4">
                      Drag and drop or click to browse
                    </div>
                    <button
                      onClick={(e) => {
                        e.stopPropagation()
                        fileInputRef.current?.click()
                      }}
                      className="px-6 py-2 bg-gradient-to-r from-emerald-600 to-green-600 hover:from-emerald-700 hover:to-green-700 text-white rounded-xl transition-all duration-200 shadow-lg shadow-emerald-500/20 hover:shadow-xl hover:shadow-emerald-500/30"
                    >
                      Browse Files
                    </button>
                  </>
                )}
              </div>

              {/* Error/Success Messages */}
              {uploadError && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-4 p-4 bg-red-500/10 border border-red-500/30 rounded-xl flex items-center space-x-3"
                >
                  <AlertCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
                  <div className="text-red-400 text-sm">{uploadError}</div>
                </motion.div>
              )}

              {uploadSuccess && (
                <motion.div
                  initial={{ opacity: 0, y: -10 }}
                  animate={{ opacity: 1, y: 0 }}
                  className="mt-4 p-4 bg-green-500/10 border border-green-500/30 rounded-xl flex items-center space-x-3"
                >
                  <CheckCircle className="w-5 h-5 text-green-400 flex-shrink-0" />
                  <div className="text-green-400 text-sm">{uploadSuccess}</div>
                </motion.div>
              )}
            </motion.div>
          </div>
        )}

        {/* Active Jobs */}
        {selectedCompanyId && jobs.length > 0 && (
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

      {/* Job Start Dialog */}
      {selectedSource && selectedCompanyId && (
        <JobStartDialog
          isOpen={jobDialogOpen}
          onClose={() => setJobDialogOpen(false)}
          source={selectedSource}
          companyId={selectedCompanyId}
          companyData={selectedCompanyData}
          onJobStarted={handleJobStarted}
        />
      )}
    </div>
  )
}
