'use client'

import { useState, useEffect, useRef } from 'react'
import { useRouter } from 'next/navigation'
import { motion } from 'framer-motion'
import { Upload, FileText, CheckCircle, XCircle, Loader2, Database, Info, Trash2 } from 'lucide-react'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'
import type { UserDataset, UserDatasetUploadResponse } from '@/types/user-dataset'

export default function DatasetsPage() {
  const router = useRouter()
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const [datasets, setDatasets] = useState<UserDataset[]>([])
  const [loading, setLoading] = useState(true)
  const [uploading, setUploading] = useState(false)
  const [uploadError, setUploadError] = useState<string | null>(null)
  const [uploadSuccess, setUploadSuccess] = useState<string | null>(null)
  const [tableName, setTableName] = useState('')
  const [dragActive, setDragActive] = useState(false)
  const fileInputRef = useRef<HTMLInputElement>(null)
  const [deleteConfirm, setDeleteConfirm] = useState<{ id: string; name: string } | null>(null)
  const [deleting, setDeleting] = useState(false)

  // Extract friendly table name from __user_{user_id}_{name} format
  const getFriendlyTableName = (tableName: string): string => {
    // Format: __user_user_33gdey7n9vlwazkubrgds1yy4ls_total_war_units
    // We want: total_war_units
    if (tableName.startsWith('__user_user_')) {
      // Remove the __user_user_ prefix and the user ID
      const withoutPrefix = tableName.substring(12) // Remove '__user_user_'
      // Find the next underscore after the user ID
      const nextUnderscore = withoutPrefix.indexOf('_')
      if (nextUnderscore !== -1) {
        return withoutPrefix.substring(nextUnderscore + 1)
      }
    }
    return tableName
  }

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.push('/sign-in')
    }
  }, [isLoaded, isSignedIn, router])

  useEffect(() => {
    const fetchDatasets = async () => {
      if (!isSignedIn) return

      try {
        const token = await getToken()
        const api = createApiClient(token)
        const response = await api.listUserDatasets(50, 0)
        setDatasets(response.datasets || [])
      } catch (error) {
        console.error('Failed to fetch datasets:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchDatasets()
  }, [getToken, isSignedIn])

  const handleFileSelect = async (file: File) => {
    if (!file.name.toLowerCase().endsWith('.csv')) {
      setUploadError('Only CSV files are supported')
      return
    }

    setUploading(true)
    setUploadError(null)
    setUploadSuccess(null)

    try {
      const token = await getToken()
      const api = createApiClient(token)
      // Pass table name only if provided, otherwise let backend generate it
      const nameToUse = tableName.trim() || undefined
      const response: UserDatasetUploadResponse = await api.uploadUserDataset(file, nameToUse)

      setUploadSuccess(`Successfully uploaded ${response.row_count} rows${nameToUse ? '' : ` as "${getFriendlyTableName(response.table_name)}"`}!`)
      setTableName('')
      
      // Refresh datasets list with a fresh token (upload may have taken time)
      try {
        const freshToken = await getToken()
        const freshApi = createApiClient(freshToken)
        const datasetsResponse = await freshApi.listUserDatasets(50, 0)
        setDatasets(datasetsResponse.datasets || [])
      } catch (refreshError) {
        console.error('Failed to refresh datasets list:', refreshError)
        // Don't show error to user since upload was successful
        // User can refresh page to see the new dataset
      }

      // Clear success message after 5 seconds
      setTimeout(() => setUploadSuccess(null), 5000)
    } catch (error: any) {
      // Handle specific error messages
      let errorMessage = error.message || 'Failed to upload CSV'
      
      // Check if it's a duplicate table name error (409 Conflict or message contains "already exists")
      if (error.status === 409 || (error.message && error.message.toLowerCase().includes('already exists'))) {
        const attemptedName = tableName.trim() || 'the generated name'
        errorMessage = `Dataset name "${attemptedName}" already exists. Please choose a different name.`
      }
      
      setUploadError(errorMessage)
      
      // Clear error message after 8 seconds
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

  if (!isLoaded || !isSignedIn || loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950">
        <div className="text-emerald-400 text-lg">Loading...</div>
      </div>
    )
  }

  const handleDelete = async (datasetId: string) => {
    setDeleting(true)
    try {
      const token = await getToken()
      const api = createApiClient(token)
      await api.deleteUserDataset(datasetId)
      
      // Remove from local state
      setDatasets(datasets.filter(d => d.id !== datasetId))
      setDeleteConfirm(null)
    } catch (error: any) {
      console.error('Failed to delete dataset:', error)
      alert(`Failed to delete dataset: ${error.message || 'Unknown error'}`)
    } finally {
      setDeleting(false)
    }
  }

  return (
    <div className="min-h-screen bg-gray-950 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-8">
          <h1 className="text-4xl font-bold text-white mb-2">Your Datasets</h1>
          <p className="text-white/60">Upload CSV files and explore your data with AI-powered insights</p>
        </div>

        {/* Upload Section */}
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6 mb-8"
        >
          <h2 className="text-xl font-bold text-white mb-6">Upload CSV Dataset</h2>

          {/* Table Name Input */}
          <div className="mb-4">
            <label className="block text-sm font-medium text-white/80 mb-2">
              Dataset Name (optional)
            </label>
            <input
              type="text"
              value={tableName}
              onChange={(e) => setTableName(e.target.value)}
              placeholder="e.g., products, sales (leave empty to auto-generate)"
              className="w-full px-4 py-2 bg-gray-800/50 border border-gray-700/50 rounded-xl text-white placeholder-white/40 focus:outline-none focus:border-emerald-500/50 transition-colors"
              disabled={uploading}
            />
            <p className="mt-2 text-xs text-white/40">
              If left empty, an AI will generate a descriptive name based on your CSV content
            </p>
          </div>

          {/* File Upload Area */}
          <div
            onDragEnter={handleDrag}
            onDragLeave={handleDrag}
            onDragOver={handleDrag}
            onDrop={handleDrop}
            className={`border-2 border-dashed rounded-xl p-8 text-center transition-colors ${
              dragActive
                ? 'border-emerald-500 bg-emerald-500/10'
                : 'border-gray-700 hover:border-emerald-500/50'
            }`}
          >
            <input
              ref={fileInputRef}
              type="file"
              accept=".csv"
              onChange={handleFileInputChange}
              className="hidden"
              disabled={uploading}
            />

            {uploading ? (
              <div className="flex flex-col items-center">
                <Loader2 className="w-12 h-12 text-emerald-400 animate-spin mb-4" />
                <div className="text-white font-medium">Uploading and processing...</div>
                <div className="text-white/40 text-sm mt-2">This may take a moment</div>
              </div>
            ) : (
              <>
                <Upload className="w-12 h-12 text-gray-400 mx-auto mb-4" />
                <div className="text-white font-medium mb-2">Upload CSV File</div>
                <div className="text-white/40 text-sm mb-4">
                  Drag and drop or click to browse
                </div>
                <button
                  onClick={() => fileInputRef.current?.click()}
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
              <XCircle className="w-5 h-5 text-red-400 flex-shrink-0" />
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

        {/* Datasets List */}
        {datasets.length > 0 ? (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6"
          >
            <h2 className="text-xl font-bold text-white mb-6">Your Datasets</h2>

            <div className="space-y-4">
              {datasets.map((dataset) => {
                const friendlyName = getFriendlyTableName(dataset.table_name)
                const fieldMetadata = dataset.field_metadata || []
                
                return (
                  <motion.div
                    key={dataset.id}
                    initial={{ opacity: 0 }}
                    animate={{ opacity: 1 }}
                    className="p-4 bg-gray-800/50 border border-gray-700/50 rounded-xl hover:border-emerald-500/30 transition-colors"
                  >
                    <div className="flex items-start justify-between mb-3">
                      <div 
                        className="flex items-start space-x-3 flex-1 cursor-pointer"
                        onClick={() => router.push(`/datasets/${dataset.id}`)}
                      >
                        <Database className="w-5 h-5 text-emerald-400 mt-1 flex-shrink-0" />
                        <div>
                          <h3 className="text-white font-semibold">{friendlyName}</h3>
                          <p className="text-white/60 text-sm mt-1">
                            {dataset.origin} • {dataset.row_count.toLocaleString()} rows
                          </p>
                          {dataset.description && (
                            <p className="text-white/40 text-sm mt-2 line-clamp-2">{dataset.description}</p>
                          )}
                        </div>
                      </div>
                      <div className="flex items-center space-x-3">
                        <div className="text-white/40 text-xs">
                          {dataset.created_at
                            ? new Date(dataset.created_at).toLocaleDateString()
                            : 'Unknown'}
                        </div>
                        <button
                          onClick={(e) => {
                            e.stopPropagation()
                            setDeleteConfirm({ id: dataset.id, name: friendlyName })
                          }}
                          className="p-2 bg-red-500/10 hover:bg-red-500/20 border border-red-500/20 hover:border-red-500/30 text-red-400 rounded-lg transition-colors"
                          title="Delete dataset"
                        >
                          <Trash2 className="w-4 h-4" />
                        </button>
                      </div>
                    </div>

                    {/* Field Metadata Preview */}
                    {fieldMetadata.length > 0 && (
                      <div className="mt-4 pt-4 border-t border-gray-700/50">
                        <div className="flex items-center space-x-2 mb-2">
                          <Info className="w-4 h-4 text-emerald-400" />
                          <span className="text-white/60 text-sm font-medium">
                            {fieldMetadata.length} fields analyzed
                          </span>
                        </div>
                        <div className="flex flex-wrap gap-2">
                          {fieldMetadata.slice(0, 5).map((field, idx) => (
                            <span
                              key={idx}
                              className="px-2 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded text-xs text-emerald-400"
                            >
                              {field.field_name} ({field.data_type})
                            </span>
                          ))}
                          {fieldMetadata.length > 5 && (
                            <span className="px-2 py-1 bg-gray-700/50 rounded text-xs text-white/40">
                              +{fieldMetadata.length - 5} more
                            </span>
                          )}
                        </div>
                      </div>
                    )}
                  </motion.div>
                )
              })}
            </div>
          </motion.div>
        ) : (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: 0.1 }}
            className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-12 text-center"
          >
            <FileText className="w-16 h-16 text-gray-400 mx-auto mb-4" />
            <h3 className="text-xl font-semibold text-white mb-2">No datasets yet</h3>
            <p className="text-white/60">
              Upload your first CSV file to get started with AI-powered data analysis
            </p>
          </motion.div>
        )}

        {/* Delete Confirmation Dialog */}
        {deleteConfirm && (
          <div className="fixed inset-0 bg-black/50 flex items-center justify-center z-50 p-4">
            <motion.div
              initial={{ opacity: 0, scale: 0.95 }}
              animate={{ opacity: 1, scale: 1 }}
              className="bg-gray-900 border border-gray-800 rounded-xl p-6 max-w-md w-full"
            >
              <div className="flex items-start space-x-4 mb-4">
                <div className="p-3 bg-red-500/10 border border-red-500/20 rounded-lg">
                  <Trash2 className="w-6 h-6 text-red-400" />
                </div>
                <div className="flex-1">
                  <h3 className="text-xl font-bold text-white mb-2">Delete Dataset</h3>
                  <p className="text-white/80">
                    Are you sure you want to delete <span className="font-semibold text-emerald-400">{deleteConfirm.name}</span>?
                  </p>
                  <p className="text-white/60 text-sm mt-2">
                    This will permanently delete the dataset, all its data, and the associated database table.
                  </p>
                  <p className="text-red-400 text-sm mt-3 font-medium">
                    ⚠️ This action cannot be undone.
                  </p>
                </div>
              </div>
              <div className="flex space-x-3 mt-6">
                <button
                  onClick={() => setDeleteConfirm(null)}
                  disabled={deleting}
                  className="flex-1 px-4 py-2 bg-gray-800 hover:bg-gray-700 text-white rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed"
                >
                  Cancel
                </button>
                <button
                  onClick={() => handleDelete(deleteConfirm.id)}
                  disabled={deleting}
                  className="flex-1 px-4 py-2 bg-red-500 hover:bg-red-600 text-white rounded-xl transition-colors disabled:opacity-50 disabled:cursor-not-allowed flex items-center justify-center space-x-2"
                >
                  {deleting ? (
                    <>
                      <Loader2 className="w-4 h-4 animate-spin" />
                      <span>Deleting...</span>
                    </>
                  ) : (
                    <>
                      <Trash2 className="w-4 h-4" />
                      <span>Delete</span>
                    </>
                  )}
                </button>
              </div>
            </motion.div>
          </div>
        )}
      </div>
    </div>
  )
}

