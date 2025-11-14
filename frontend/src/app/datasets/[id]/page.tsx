'use client'

import { useState, useEffect, useMemo } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { ArrowLeft, Database, Table as TableIcon, FileText, Loader2, Settings } from 'lucide-react'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'
import type { UserDataset, FieldMetadata } from '@/types/user-dataset'
import { DataTable } from '@/components/ui/data-table'
import { ColumnDef } from '@tanstack/react-table'
import ReactMarkdown from 'react-markdown'
import remarkGfm from 'remark-gfm'

type TabType = 'table' | 'metadata' | 'configuration'

export default function DatasetDetailPage() {
  const router = useRouter()
  const params = useParams()
  const { isLoaded, isSignedIn, getToken } = useAuth()
  const datasetId = params?.id as string

  const [dataset, setDataset] = useState<UserDataset | null>(null)
  const [data, setData] = useState<any[]>([])
  const [columns, setColumns] = useState<string[]>([])
  const [loading, setLoading] = useState(true)
  const [dataLoading, setDataLoading] = useState(false)
  const [activeTab, setActiveTab] = useState<TabType>('table')
  const [totalRows, setTotalRows] = useState(0)

  useEffect(() => {
    if (isLoaded && !isSignedIn) {
      router.push('/sign-in')
    }
  }, [isLoaded, isSignedIn, router])

  useEffect(() => {
    const fetchDataset = async () => {
      if (!isSignedIn || !datasetId) return

      try {
        const token = await getToken()
        const api = createApiClient(token)
        const datasetData = await api.getUserDataset(datasetId)
        setDataset(datasetData)
      } catch (error) {
        console.error('Failed to fetch dataset:', error)
      } finally {
        setLoading(false)
      }
    }

    fetchDataset()
  }, [getToken, isSignedIn, datasetId])

  useEffect(() => {
    const fetchData = async () => {
      if (!isSignedIn || !datasetId || activeTab !== 'table') return

      setDataLoading(true)
      try {
        const token = await getToken()
        const api = createApiClient(token)
        // Fetch more data for client-side sorting/filtering (up to 1000 rows)
        const response = await api.getDatasetData(datasetId, 1000, 0)
        setData(response.data || [])
        setColumns(response.columns || [])
        setTotalRows(response.total_rows || 0)
      } catch (error) {
        console.error('Failed to fetch dataset data:', error)
      } finally {
        setDataLoading(false)
      }
    }

    fetchData()
  }, [getToken, isSignedIn, datasetId, activeTab])

  // Create column definitions for TanStack Table
  const tableColumns = useMemo<ColumnDef<any>[]>(() => {
    if (columns.length === 0) return []

    return columns.map((col) => ({
      accessorKey: col,
      header: col,
      cell: ({ getValue }) => {
        const value = getValue()
        
        // Format display value
        if (value === null || value === undefined) {
          return <span className="text-white/30">NULL</span>
        }
        
        if (typeof value === 'object') {
          return (
            <pre className="text-xs text-emerald-400 max-w-md overflow-auto">
              {JSON.stringify(value, null, 2)}
            </pre>
          )
        }
        
        if (typeof value === 'boolean') {
          return (
            <span className={value ? 'text-green-400' : 'text-red-400'}>
              {String(value)}
            </span>
          )
        }
        
        if (typeof value === 'number') {
          return <span className="text-blue-400">{value.toLocaleString()}</span>
        }
        
        return <span>{String(value)}</span>
      },
      enableSorting: true,
      enableColumnFilter: true,
    }))
  }, [columns])

  if (!isLoaded || !isSignedIn || loading) {
    return (
      <div className="flex items-center justify-center h-screen bg-gray-950">
        <div className="text-emerald-400 text-lg">Loading...</div>
      </div>
    )
  }

  if (!dataset) {
    return (
      <div className="min-h-screen bg-gray-950 p-8">
        <div className="max-w-7xl mx-auto">
          <div className="text-center py-20">
            <p className="text-white/60">Dataset not found</p>
            <button
              onClick={() => router.push('/datasets')}
              className="mt-4 px-4 py-2 bg-emerald-500/20 hover:bg-emerald-500/30 text-emerald-400 rounded-xl transition-colors"
            >
              Back to Datasets
            </button>
          </div>
        </div>
      </div>
    )
  }

  const fieldMetadata = dataset.field_metadata || []

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

  // Convert HTML tags to markdown formatting for better rendering
  const cleanDescription = (description: string): string => {
    if (!description) return ''
    
    let cleaned = description
    
    // Replace full table names with friendly names first
    if (dataset.table_name) {
      const friendlyName = getFriendlyTableName(dataset.table_name)
      const escapedTableName = dataset.table_name.replace(/[.*+?^${}()|[\]\\]/g, '\\$&')
      cleaned = cleaned.replace(new RegExp(escapedTableName, 'g'), `\`${friendlyName}\``)
    }
    
    // Convert <span style="color:teal"> or similar to backticks for code highlighting
    cleaned = cleaned.replace(/<span[^>]*style="color:[^"]*"[^>]*>(.*?)<\/span>/gi, '`$1`')
    
    // Remove <object> tags but keep content
    cleaned = cleaned.replace(/<\/?object>/gi, '')
    
    // Convert any remaining HTML tags to markdown equivalents or remove them
    cleaned = cleaned.replace(/<strong>(.*?)<\/strong>/gi, '**$1**')
    cleaned = cleaned.replace(/<em>(.*?)<\/em>/gi, '*$1*')
    cleaned = cleaned.replace(/<code>(.*?)<\/code>/gi, '`$1`')
    
    // Remove any remaining HTML tags
    cleaned = cleaned.replace(/<[^>]*>/g, '')
    
    return cleaned
  }

  const friendlyTableName = getFriendlyTableName(dataset.table_name)

  return (
    <div className="min-h-screen bg-gray-950 p-8">
      <div className="max-w-7xl mx-auto">
        {/* Header */}
        <div className="mb-6">
          <button
            onClick={() => router.push('/datasets')}
            className="flex items-center space-x-2 text-white/60 hover:text-white mb-4 transition-colors"
          >
            <ArrowLeft className="w-4 h-4" />
            <span>Back to Datasets</span>
          </button>
          <div className="flex items-center space-x-3 mb-2">
            <Database className="w-8 h-8 text-emerald-400" />
            <h1 className="text-3xl font-bold text-white">{friendlyTableName}</h1>
          </div>
          <p className="text-white/60">
            {dataset.origin} • {dataset.row_count.toLocaleString()} rows
          </p>
        </div>

        {/* Tabs */}
        <div className="mb-6 flex space-x-2 border-b border-gray-800">
          <button
            onClick={() => setActiveTab('table')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'table'
                ? 'text-emerald-400 border-b-2 border-emerald-400'
                : 'text-white/60 hover:text-white'
            }`}
          >
            <div className="flex items-center space-x-2">
              <TableIcon className="w-4 h-4" />
              <span>Table</span>
            </div>
          </button>
          <button
            onClick={() => setActiveTab('metadata')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'metadata'
                ? 'text-emerald-400 border-b-2 border-emerald-400'
                : 'text-white/60 hover:text-white'
            }`}
          >
            <div className="flex items-center space-x-2">
              <FileText className="w-4 h-4" />
              <span>Metadata</span>
            </div>
          </button>
          <button
            onClick={() => setActiveTab('configuration')}
            className={`px-6 py-3 font-medium transition-colors ${
              activeTab === 'configuration'
                ? 'text-emerald-400 border-b-2 border-emerald-400'
                : 'text-white/60 hover:text-white'
            }`}
          >
            <div className="flex items-center space-x-2">
              <Settings className="w-4 h-4" />
              <span>Configuration</span>
            </div>
          </button>
        </div>

        {/* Content */}
        {activeTab === 'table' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6"
          >
            {dataLoading ? (
              <div className="flex items-center justify-center py-20">
                <Loader2 className="w-8 h-8 text-emerald-400 animate-spin" />
              </div>
            ) : (
              <>
                {columns.length > 0 && data.length > 0 ? (
                  <DataTable
                    data={data}
                    columns={tableColumns}
                    pageSize={50}
                    enableSorting={true}
                    enableFiltering={true}
                  />
                ) : (
                  <div className="text-center py-20 text-white/60">No data available</div>
                )}
              </>
            )}
          </motion.div>
        )}

        {activeTab === 'metadata' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6"
          >
            {/* Summary */}
            {dataset.description && (
              <div className="mb-8">
                <h2 className="text-xl font-bold text-white mb-4">Summary</h2>
                <div className="prose prose-invert prose-emerald max-w-none">
                  <ReactMarkdown 
                    remarkPlugins={[remarkGfm]}
                    className="text-white/80 leading-relaxed"
                    components={{
                      p: ({ children }) => <p className="mb-4 last:mb-0">{children}</p>,
                      strong: ({ children }) => <strong className="text-emerald-400 font-semibold">{children}</strong>,
                      em: ({ children }) => <em className="text-blue-400">{children}</em>,
                      code: ({ children }) => <code className="px-1.5 py-0.5 bg-gray-800 rounded text-emerald-400 text-sm font-mono">{children}</code>,
                      ul: ({ children }) => <ul className="list-disc list-inside space-y-1 mb-4">{children}</ul>,
                      ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 mb-4">{children}</ol>,
                      li: ({ children }) => <li className="text-white/80">{children}</li>,
                      h1: ({ children }) => <h1 className="text-2xl font-bold text-white mb-3">{children}</h1>,
                      h2: ({ children }) => <h2 className="text-xl font-bold text-white mb-2">{children}</h2>,
                      h3: ({ children }) => <h3 className="text-lg font-semibold text-white mb-2">{children}</h3>,
                      blockquote: ({ children }) => <blockquote className="border-l-4 border-emerald-500 pl-4 italic text-white/70">{children}</blockquote>,
                    }}
                  >
                    {cleanDescription(dataset.description)}
                  </ReactMarkdown>
                </div>
              </div>
            )}

            {/* Field Metadata */}
            {fieldMetadata.length > 0 && (
              <div>
                <h2 className="text-xl font-bold text-white mb-4">
                  Field Metadata ({fieldMetadata.length} fields)
                </h2>
                <div className="space-y-4">
                  {fieldMetadata.map((field: FieldMetadata, idx: number) => (
                    <div
                      key={idx}
                      className="p-4 bg-gray-800/50 border border-gray-700/50 rounded-xl"
                    >
                      <div className="flex items-start justify-between mb-2">
                        <div>
                          <h3 className="text-white font-semibold text-lg">{field.field_name}</h3>
                          <span className="text-emerald-400 text-sm">{field.data_type}</span>
                        </div>
                        {field.unique_value_count !== null && field.unique_value_count !== undefined && (
                          <div className="text-white/60 text-sm">
                            {field.unique_value_count.toLocaleString()} unique values
                          </div>
                        )}
                      </div>
                      <p className="text-white/80 mt-2">{field.description}</p>
                      {field.top_values && field.top_values.length > 0 && (
                        <div className="mt-4 pt-4 border-t border-gray-700/50">
                          <h4 className="text-white/60 text-sm font-medium mb-2">Top Values</h4>
                          <div className="flex flex-wrap gap-2">
                            {field.top_values.map((value, vIdx) => {
                              const displayValue = value.length > 50 ? value.substring(0, 50) + '...' : value
                              return (
                                <span
                                  key={vIdx}
                                  className="px-2 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded text-xs text-emerald-400"
                                  title={value} // Show full value on hover
                                >
                                  {displayValue}
                                </span>
                              )
                            })}
                          </div>
                        </div>
                      )}
                    </div>
                  ))}
                </div>
              </div>
            )}

            {fieldMetadata.length === 0 && !dataset.description && (
              <div className="text-center py-20 text-white/60">No metadata available</div>
            )}
          </motion.div>
        )}

        {activeTab === 'configuration' && (
          <motion.div
            initial={{ opacity: 0, y: 20 }}
            animate={{ opacity: 1, y: 0 }}
            className="space-y-6"
          >
            {/* Vector Store Configuration */}
            <div className="bg-gray-900/50 border border-gray-800/50 rounded-xl p-6">
              <h2 className="text-xl font-bold text-white mb-4">Vector Store Configuration</h2>
              
              {dataset.vector_store_columns ? (
                <div className="space-y-6">
                  {/* Global Vectorizer */}
                  <div className="p-4 bg-gray-800/50 border border-gray-700/50 rounded-xl">
                    <div className="flex items-center justify-between mb-4">
                      <h3 className="text-white font-semibold">Global Vectorizer</h3>
                      <span className="px-3 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded-lg text-emerald-400 text-sm font-medium">
                        TEXT2VEC_OPENAI
                      </span>
                    </div>
                    <div className="flex items-center space-x-2">
                      <Database className="w-5 h-5 text-emerald-400" />
                      <span className="text-white/80">text-embedding-3-small</span>
                    </div>
                  </div>

                  {/* Main Column */}
                  <div className="p-4 bg-gray-800/50 border border-gray-700/50 rounded-xl">
                    <h3 className="text-white font-semibold mb-2">Primary Text Column</h3>
                    <div className="flex items-center space-x-2 mb-3">
                      <span className="px-3 py-1 bg-blue-500/10 border border-blue-500/20 rounded text-blue-400 font-mono text-sm">
                        {dataset.vector_store_columns.main_column}
                      </span>
                    </div>
                    <p className="text-white/60 text-sm">
                      This column will be used for semantic search and vector embeddings.
                    </p>
                  </div>

                  {/* Alternative Columns */}
                  {dataset.vector_store_columns.alternative_columns.length > 0 && (
                    <div className="p-4 bg-gray-800/50 border border-gray-700/50 rounded-xl">
                      <h3 className="text-white font-semibold mb-2">Alternative Columns</h3>
                      <div className="flex flex-wrap gap-2 mb-3">
                        {dataset.vector_store_columns.alternative_columns.map((col, idx) => (
                          <span
                            key={idx}
                            className="px-3 py-1 bg-purple-500/10 border border-purple-500/20 rounded text-purple-400 font-mono text-sm"
                          >
                            {col}
                          </span>
                        ))}
                      </div>
                      <p className="text-white/60 text-sm">
                        These columns can be concatenated with the main column for richer semantic search.
                      </p>
                    </div>
                  )}

                  {/* Description */}
                  <div className="p-4 bg-gray-800/50 border border-gray-700/50 rounded-xl">
                    <h3 className="text-white font-semibold mb-2">Why These Columns?</h3>
                    <div className="prose prose-invert prose-emerald max-w-none">
                      <ReactMarkdown 
                        remarkPlugins={[remarkGfm]}
                        className="text-white/80 leading-relaxed"
                        components={{
                          p: ({ children }) => <p className="mb-2 last:mb-0">{children}</p>,
                          strong: ({ children }) => <strong className="text-emerald-400 font-semibold">{children}</strong>,
                          em: ({ children }) => <em className="text-blue-400">{children}</em>,
                          code: ({ children }) => <code className="px-1.5 py-0.5 bg-gray-700 rounded text-emerald-400 text-sm font-mono">{children}</code>,
                          ul: ({ children }) => <ul className="list-disc list-inside space-y-1 mb-2">{children}</ul>,
                          ol: ({ children }) => <ol className="list-decimal list-inside space-y-1 mb-2">{children}</ol>,
                          li: ({ children }) => <li className="text-white/80">{children}</li>,
                        }}
                      >
                        {cleanDescription(dataset.vector_store_columns.description)}
                      </ReactMarkdown>
                    </div>
                  </div>
                </div>
              ) : (
                <div className="text-center py-12">
                  <Database className="w-12 h-12 text-white/20 mx-auto mb-4" />
                  <p className="text-white/60">No vector store columns configured</p>
                  <p className="text-white/40 text-sm mt-2">
                    This dataset doesn't have suitable text columns for semantic search
                  </p>
                </div>
              )}
            </div>
          </motion.div>
        )}
      </div>
    </div>
  )
}

