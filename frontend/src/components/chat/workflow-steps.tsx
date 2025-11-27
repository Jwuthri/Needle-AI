'use client'

import { useState } from 'react'
import { motion } from 'framer-motion'
import { ChevronDown, ChevronUp, Loader, Wrench } from 'lucide-react'
import { MarkdownRenderer } from './markdown-renderer'
import { formatRawOutput, formatToolContent, formatAgentName } from './workflow-utils'

interface AgentStep {
  step_id: string
  agent_name: string
  content: any
  is_structured: boolean
  step_order?: number
  status?: 'started' | 'active' | 'completed' | 'error'
  timestamp?: string
  raw_output?: string
}

interface WorkflowStepsProps {
  steps: AgentStep[]
  currentContent?: string | null // For streaming content override
  expanded?: boolean // Whether the whole container is expanded (passed from parent)
}

export function WorkflowSteps({ steps, currentContent, expanded = true }: WorkflowStepsProps) {
  // Local state to track which individual steps are expanded
  // We default to expanding active steps
  const [expandedStepIds, setExpandedStepIds] = useState<Set<string>>(new Set())

  // Helper to toggle step expansion
  const toggleStep = (stepId: string) => {
    setExpandedStepIds((prev) => {
      const next = new Set(prev)
      if (next.has(stepId)) {
        next.delete(stepId)
      } else {
        next.add(stepId)
      }
      return next
    })
  }

  if (!expanded || steps.length === 0) {
    return null
  }

  // Filter out REPORTER and steps with no meaningful content
  const meaningfulSteps = steps.filter(step => {
    // Filter out REPORTER agent - it should only appear in answer area, not workflow
    if (step.agent_name?.toUpperCase() === 'REPORTER') {
      return false
    }
    
    // Always show active steps (they're processing)
    if (step.status === 'active' || step.status === 'started') {
      return true
    }
    
    // Show structured steps (tool calls) that have content
    if (step.is_structured && step.content) {
      return true
    }
    
    // Show steps with text content
    if (step.content && typeof step.content === 'string' && step.content.trim()) {
      return true
    }
    
    // Hide steps with no meaningful content
    return false
  })

  if (meaningfulSteps.length === 0) {
    return null
  }

  return (
    <div className="px-6 pb-4 space-y-4 border-t border-purple-500/20 pt-4">
      {meaningfulSteps.map((step, index) => {
        // Determine if this step is "active" (currently streaming or processing)
        const isActive = step.status === 'active' || step.status === 'started'
        
        // Determine if this step should be expanded
        // Active steps are ALWAYS expanded to show real-time progress
        // For completed steps, check if user manually expanded them
        const stepId = step.step_id
        const isExpanded = isActive || expandedStepIds.has(stepId)

        return (
          <div key={stepId}>
            <div className={`bg-gray-900/40 border ${isActive ? 'border-purple-500/40 shadow-[0_0_15px_-3px_rgba(168,85,247,0.15)]' : 'border-gray-700/50'} rounded-lg overflow-hidden transition-all duration-300`}>
              {/* Panel Header - Click to toggle */}
              <button
                onClick={() => toggleStep(stepId)}
                className="w-full bg-gray-800/50 px-3 py-2 border-b border-gray-700/50 flex items-center justify-between hover:bg-gray-800/80 transition-colors"
              >
                <div className="flex items-center gap-2">
                  {/* Status icon with relevant emoji */}
                  {isActive ? (
                    step.is_structured ? (
                      <span className="text-sm">🔧</span>
                    ) : (
                      <span className="text-sm">🧠</span>
                    )
                  ) : step.status === 'error' ? (
                    <span className="text-sm">❌</span>
                  ) : (
                    <span className="text-sm">✅</span>
                  )}
                  <span className="text-xs font-mono text-purple-300 font-bold uppercase tracking-wider">
                    {formatAgentName(step.agent_name)}
                  </span>
                </div>

                <div className="flex items-center gap-2">
                  <span className="text-[10px] text-gray-500 font-mono">
                    {step.is_structured ? (formatAgentName(step.content?.tool_name) || 'Tool Call') : 'Thinking'}
                  </span>
                  {isExpanded ? (
                    <ChevronUp className="w-3 h-3 text-gray-500" />
                  ) : (
                    <ChevronDown className="w-3 h-3 text-gray-500" />
                  )}
                </div>
              </button>

              {/* Panel Content - Collapsible */}
              <motion.div
                initial={false}
                animate={{ height: isExpanded ? 'auto' : 0, opacity: isExpanded ? 1 : 0 }}
                transition={{ duration: 0.2 }}
                className="overflow-hidden"
              >
                <div className="p-3 bg-black/20">
                  {/* For active (streaming) steps, show the content from step.content directly */}
                  {isActive && !step.is_structured ? (
                    // Text content streaming
                    step.content && typeof step.content === 'string' && step.content.trim() ? (
                      <div className="text-sm text-gray-200 prose prose-invert prose-sm max-w-none">
                        <MarkdownRenderer content={step.content} />
                        <span className="inline-block w-2 h-4 bg-purple-400 ml-1 animate-pulse"></span>
                      </div>
                    ) : (
                      <div className="flex items-center space-x-2 text-purple-300">
                        <Loader className="w-3 h-3 animate-spin" />
                        <span className="text-xs italic">Processing...</span>
                      </div>
                    )
                  ) : step.is_structured && step.content ? (
                    <div className="text-sm text-gray-200 prose prose-invert prose-sm max-w-none">
                      {(() => {
                        const toolName = step.content.tool_name || step.agent_name;
                        return (
                          <div className="space-y-2">
                            <div className="flex items-center gap-2 text-purple-300">
                              <Wrench className="w-3 h-3" />
                              <span>{toolName}</span>
                            </div>
                            {step.content.tool_kwargs && (
                              <div className="pl-5 text-gray-400">
                                {Object.entries(step.content.tool_kwargs).map(([k, v]) => (
                                  <div key={k} className="flex gap-2">
                                    <span className="text-gray-500">{k}:</span>
                                    <span className="text-gray-300">{String(v)}</span>
                                  </div>
                                ))}
                              </div>
                            )}
                            {step.raw_output && (
                              <div className="mt-2 pl-5 border-l-2 border-gray-700/50">
                                <div className="text-[10px] text-gray-500 mb-1">RESULT</div>
                                <div className="text-gray-300 max-h-40 overflow-y-auto custom-scrollbar">
                                  {formatRawOutput(step.raw_output)}
                                </div>
                              </div>
                            )}
                          </div>
                        );
                      })()}
                    </div>
                  ) : step.content && typeof step.content === 'string' ? (
                    <div className="text-sm text-gray-200 prose prose-invert prose-sm max-w-none">
                      <MarkdownRenderer content={step.content} />
                    </div>
                  ) : null}
                </div>
              </motion.div>
            </div>
          </div>
        )
      })}
    </div>
  )
}

