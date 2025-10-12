'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, Clock, CheckCircle, XCircle, Circle, Loader } from 'lucide-react';

interface ExecutionNode {
  id: string;
  name: string;
  type: string;
  status: string;
  start_time?: string;
  end_time?: string;
  duration_ms?: number;
  input_summary?: string;
  output_summary?: string;
  error?: string;
  metadata?: Record<string, any>;
  children: ExecutionNode[];
}

interface ExecutionTreeData {
  tree_id: string;
  query: string;
  session_id?: string;
  created_at: string;
  root: ExecutionNode;
}

interface ExecutionTreeProps {
  tree: ExecutionTreeData;
  className?: string;
}

interface ExecutionNodeProps {
  node: ExecutionNode;
  level?: number;
}

const ExecutionNodeComponent = ({ node, level = 0 }: ExecutionNodeProps) => {
  const [isExpanded, setIsExpanded] = useState(level < 2); // Auto-expand first 2 levels

  const getStatusIcon = (status: string) => {
    switch (status) {
      case 'completed':
        return <CheckCircle className="w-4 h-4 text-green-500" />;
      case 'failed':
        return <XCircle className="w-4 h-4 text-red-500" />;
      case 'running':
        return <Loader className="w-4 h-4 text-blue-500 animate-spin" />;
      case 'pending':
        return <Circle className="w-4 h-4 text-gray-400" />;
      default:
        return <Circle className="w-4 h-4 text-gray-400" />;
    }
  };

  const getStatusColor = (status: string) => {
    switch (status) {
      case 'completed':
        return 'bg-green-50 border-green-200';
      case 'failed':
        return 'bg-red-50 border-red-200';
      case 'running':
        return 'bg-blue-50 border-blue-200';
      case 'pending':
        return 'bg-gray-50 border-gray-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  const getTypeColor = (type: string) => {
    switch (type) {
      case 'tool':
        return 'bg-purple-100 text-purple-800';
      case 'agent':
        return 'bg-blue-100 text-blue-800';
      case 'decision':
        return 'bg-yellow-100 text-yellow-800';
      case 'synthesis':
        return 'bg-green-100 text-green-800';
      default:
        return 'bg-gray-100 text-gray-800';
    }
  };

  const hasChildren = node.children && node.children.length > 0;

  return (
    <div className={`${level > 0 ? 'ml-6 mt-2' : 'mt-2'}`}>
      <div
        className={`border rounded-lg p-3 ${getStatusColor(node.status)} cursor-pointer hover:shadow-sm transition-shadow`}
        onClick={() => hasChildren && setIsExpanded(!isExpanded)}
      >
        <div className="flex items-start gap-3">
          {/* Expand/Collapse Icon */}
          <div className="flex-shrink-0 mt-0.5">
            {hasChildren ? (
              isExpanded ? (
                <ChevronDown className="w-4 h-4 text-gray-500" />
              ) : (
                <ChevronRight className="w-4 h-4 text-gray-500" />
              )
            ) : (
              <div className="w-4" />
            )}
          </div>

          {/* Status Icon */}
          <div className="flex-shrink-0 mt-0.5">{getStatusIcon(node.status)}</div>

          {/* Node Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <h4 className="font-medium text-sm text-gray-900">{node.name}</h4>
              <span
                className={`text-xs px-2 py-0.5 rounded-full ${getTypeColor(node.type)}`}
              >
                {node.type}
              </span>
              {node.duration_ms !== undefined && (
                <span className="text-xs text-gray-500 flex items-center gap-1">
                  <Clock className="w-3 h-3" />
                  {node.duration_ms}ms
                </span>
              )}
            </div>

            {/* Input Summary */}
            {node.input_summary && (
              <p className="text-xs text-gray-600 mt-1">
                <span className="font-medium">Input:</span> {node.input_summary}
              </p>
            )}

            {/* Output Summary */}
            {node.output_summary && (
              <p className="text-xs text-gray-700 mt-1 font-medium">
                <span className="font-medium">Output:</span> {node.output_summary}
              </p>
            )}

            {/* Error */}
            {node.error && (
              <p className="text-xs text-red-600 mt-1 font-medium">
                <span className="font-medium">Error:</span> {node.error}
              </p>
            )}

            {/* Metadata */}
            {node.metadata && Object.keys(node.metadata).length > 0 && (
              <div className="text-xs text-gray-500 mt-2">
                {Object.entries(node.metadata).map(([key, value]) => (
                  <div key={key} className="inline-block mr-3">
                    <span className="font-medium">{key}:</span> {String(value)}
                  </div>
                ))}
              </div>
            )}
          </div>
        </div>
      </div>

      {/* Children */}
      {isExpanded && hasChildren && (
        <div className="border-l-2 border-gray-200 ml-3">
          {node.children.map((child) => (
            <ExecutionNodeComponent key={child.id} node={child} level={level + 1} />
          ))}
        </div>
      )}
    </div>
  );
};

export const ExecutionTree = ({ tree, className = '' }: ExecutionTreeProps) => {
  const [isOpen, setIsOpen] = useState(false);

  if (!tree || !tree.root) {
    return null;
  }

  const stats = {
    total_duration: tree.root.duration_ms || 0,
    status: tree.root.status,
  };

  return (
    <div className={`border border-gray-200 rounded-lg bg-white ${className}`}>
      {/* Header */}
      <div
        className="flex items-center justify-between p-4 cursor-pointer hover:bg-gray-50"
        onClick={() => setIsOpen(!isOpen)}
      >
        <div className="flex items-center gap-3">
          {isOpen ? (
            <ChevronDown className="w-5 h-5 text-gray-500" />
          ) : (
            <ChevronRight className="w-5 h-5 text-gray-500" />
          )}
          <h3 className="font-semibold text-gray-900">Execution Steps</h3>
          <span className="text-xs text-gray-500 flex items-center gap-1">
            <Clock className="w-3 h-3" />
            {stats.total_duration}ms
          </span>
        </div>
        <div className="flex items-center gap-2">
          {stats.status === 'completed' && (
            <span className="text-xs text-green-600 font-medium">Completed</span>
          )}
          {stats.status === 'failed' && (
            <span className="text-xs text-red-600 font-medium">Failed</span>
          )}
        </div>
      </div>

      {/* Execution Tree */}
      {isOpen && (
        <div className="p-4 pt-0 border-t border-gray-100">
          <ExecutionNodeComponent node={tree.root} />
        </div>
      )}
    </div>
  );
};

export default ExecutionTree;

