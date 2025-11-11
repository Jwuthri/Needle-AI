'use client'

import { useState, useEffect, useMemo } from 'react'
import { useRouter, useParams } from 'next/navigation'
import { motion } from 'framer-motion'
import { ArrowLeft, Database, Table as TableIcon, FileText, Loader2 } from 'lucide-react'
import { useAuth } from '@clerk/nextjs'
import { createApiClient } from '@/lib/api'
import type { UserDataset, FieldMetadata } from '@/types/user-dataset'
import { DataTable } from '@/components/ui/data-table'
import { ColumnDef } from '@tanstack/react-table'

type TabType = 'table' | 'metadata'

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

  const fieldMetadata = dataset.meta?.field_metadata || []

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
            <h1 className="text-3xl font-bold text-white">{dataset.table_name}</h1>
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
                <p className="text-white/80 leading-relaxed">{dataset.description}</p>
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
                        {field.unique_value_count !== null && (
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
                            {field.top_values.map((value, vIdx) => (
                              <span
                                key={vIdx}
                                className="px-2 py-1 bg-emerald-500/10 border border-emerald-500/20 rounded text-xs text-emerald-400"
                              >
                                {value}
                              </span>
                            ))}
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
      </div>
    </div>
  )
}

