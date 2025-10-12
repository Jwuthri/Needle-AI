'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { CheckCircle, Clock, XCircle, ChevronDown, ChevronUp } from 'lucide-react'
import { QueryPipelineStep, EnhancedChatMessage } from '@/types/chat'

interface PipelineVisualizerProps {
  steps: QueryPipelineStep[]
  message: EnhancedChatMessage
}

export function PipelineVisualizer({ steps, message }: PipelineVisualizerProps) {
  const [expandedStep, setExpandedStep] = useState<number | null>(null)

  const getStatusIcon = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
      case 'success':
        return <CheckCircle className="w-6 h-6 text-emerald-400" />
      case 'running':
      case 'processing':
        return <Clock className="w-6 h-6 text-yellow-400 animate-spin" />
      case 'failed':
      case 'error':
        return <XCircle className="w-6 h-6 text-red-400" />
      default:
        return <Clock className="w-6 h-6 text-gray-400" />
    }
  }

  const getStatusColor = (status: string) => {
    switch (status.toLowerCase()) {
      case 'completed':
      case 'success':
        return 'border-emerald-500/50 bg-emerald-500/10'
      case 'running':
      case 'processing':
        return 'border-yellow-500/50 bg-yellow-500/10'
      case 'failed':
      case 'error':
        return 'border-red-500/50 bg-red-500/10'
      default:
        return 'border-gray-700/50 bg-gray-800/30'
    }
  }

  const totalDuration = steps.reduce((sum, step) => sum + step.duration_ms, 0)

  return (
    <div className="max-w-4xl mx-auto">
      {/* Header */}
      <div className="mb-8">
        <h2 className="text-2xl font-bold text-white mb-2">Query Pipeline</h2>
        <div className="flex items-center space-x-4 text-sm text-white/60">
          <span>{steps.length} steps</span>
          <span>•</span>
          <span>Total: {totalDuration.toFixed(0)}ms</span>
          {message.query_type && (
            <>
              <span>•</span>
              <span className="text-emerald-400">{message.query_type}</span>
            </>
          )}
        </div>
      </div>

      {/* Pipeline Steps */}
      <div className="space-y-6">
        {steps.map((step, index) => {
          const isExpanded = expandedStep === index
          const isCompleted = step.status.toLowerCase() === 'completed' || step.status.toLowerCase() === 'success'

          return (
            <motion.div
              key={index}
              initial={{ opacity: 0, y: 20 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: index * 0.1 }}
            >
              {/* Connection Line */}
              {index > 0 && (
                <div className="flex justify-center mb-6">
                  <motion.div
                    initial={{ height: 0 }}
                    animate={{ height: 40 }}
                    transition={{ delay: index * 0.1 - 0.05 }}
                    className="w-0.5 bg-gradient-to-b from-emerald-500/30 to-emerald-500/10"
                    style={{
                      backgroundImage: 'repeating-linear-gradient(0deg, #10b981 0px, #10b981 4px, transparent 4px, transparent 8px)',
                    }}
                  />
                </div>
              )}

              {/* Step Card */}
              <div className={`border-2 rounded-xl overflow-hidden transition-all ${getStatusColor(step.status)} ${
                isCompleted ? 'hover:border-emerald-500' : ''
              }`}>
                <button
                  onClick={() => setExpandedStep(isExpanded ? null : index)}
                  className="w-full p-6 flex items-center justify-between text-left hover:bg-white/5 transition-colors"
                >
                  <div className="flex items-center space-x-4 flex-1">
                    <div className="flex-shrink-0">
                      {getStatusIcon(step.status)}
                    </div>
                    <div className="flex-1">
                      <h3 className="text-lg font-semibold text-white mb-1">
                        {index + 1}. {step.name}
                      </h3>
                      <div className="flex items-center space-x-4 text-sm text-white/60">
                        <span>{step.duration_ms.toFixed(0)}ms</span>
                        <span>•</span>
                        <span className="capitalize">{step.status}</span>
                      </div>
                    </div>
                  </div>
                  {isExpanded ? (
                    <ChevronUp className="w-5 h-5 text-white/40" />
                  ) : (
                    <ChevronDown className="w-5 h-5 text-white/40" />
                  )}
                </button>

                {/* Expanded Metadata */}
                {isExpanded && step.metadata && Object.keys(step.metadata).length > 0 && (
                  <motion.div
                    initial={{ opacity: 0, height: 0 }}
                    animate={{ opacity: 1, height: 'auto' }}
                    exit={{ opacity: 0, height: 0 }}
                    className="px-6 pb-6 border-t border-gray-700/30"
                  >
                    <div className="pt-4 space-y-2">
                      <div className="text-white/60 text-sm font-medium mb-3">Metadata:</div>
                      <div className="bg-gray-900/50 rounded-lg p-4 font-mono text-sm">
                        <pre className="text-white/80 whitespace-pre-wrap overflow-x-auto">
                          {JSON.stringify(step.metadata, null, 2)}
                        </pre>
                      </div>
                    </div>
                  </motion.div>
                )}
              </div>
            </motion.div>
          )
        })}
      </div>

      {/* Summary */}
      <motion.div
        initial={{ opacity: 0, y: 20 }}
        animate={{ opacity: 1, y: 0 }}
        transition={{ delay: steps.length * 0.1 }}
        className="mt-8 p-6 bg-emerald-500/10 border border-emerald-500/30 rounded-xl"
      >
        <h3 className="text-lg font-semibold text-white mb-3">Response Generated</h3>
        <div className="text-white/80 text-sm line-clamp-3">
          {message.content}
        </div>
        {message.sources && message.sources.length > 0 && (
          <div className="mt-3 text-emerald-400 text-sm">
            Used {message.sources.length} sources
          </div>
        )}
      </motion.div>
    </div>
  )
}

