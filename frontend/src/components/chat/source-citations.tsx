'use client';

import { useState } from 'react';
import { ChevronDown, ChevronRight, ExternalLink, Quote, ThumbsUp, ThumbsDown, Minus } from 'lucide-react';

interface Citation {
  id: string;
  index: number;
  author: string;
  source: string;
  url?: string;
  date?: string;
  sentiment?: 'Positive' | 'Negative' | 'Neutral';
  relevance_score?: number;
  quote?: string;
  full_content?: string;
  citation_text?: string;
}

interface SourceCitationsProps {
  sources: Citation[];
  className?: string;
}

interface SourceItemProps {
  citation: Citation;
}

const SourceItem = ({ citation }: SourceItemProps) => {
  const [isExpanded, setIsExpanded] = useState(false);

  const getSentimentIcon = (sentiment?: string) => {
    switch (sentiment) {
      case 'Positive':
        return <ThumbsUp className="w-4 h-4 text-green-500" />;
      case 'Negative':
        return <ThumbsDown className="w-4 h-4 text-red-500" />;
      case 'Neutral':
        return <Minus className="w-4 h-4 text-gray-400" />;
      default:
        return null;
    }
  };

  const getSentimentColor = (sentiment?: string) => {
    switch (sentiment) {
      case 'Positive':
        return 'bg-green-50 border-green-200';
      case 'Negative':
        return 'bg-red-50 border-red-200';
      case 'Neutral':
        return 'bg-gray-50 border-gray-200';
      default:
        return 'bg-gray-50 border-gray-200';
    }
  };

  return (
    <div className={`border rounded-lg ${getSentimentColor(citation.sentiment)}`}>
      <div
        className="p-3 cursor-pointer hover:bg-white/50 transition-colors"
        onClick={() => setIsExpanded(!isExpanded)}
      >
        <div className="flex items-start gap-3">
          {/* Expand Icon */}
          <div className="flex-shrink-0 mt-0.5">
            {isExpanded ? (
              <ChevronDown className="w-4 h-4 text-gray-500" />
            ) : (
              <ChevronRight className="w-4 h-4 text-gray-500" />
            )}
          </div>

          {/* Sentiment Icon */}
          <div className="flex-shrink-0 mt-0.5">{getSentimentIcon(citation.sentiment)}</div>

          {/* Content */}
          <div className="flex-1 min-w-0">
            <div className="flex items-center gap-2 flex-wrap">
              <span className="font-medium text-sm text-gray-900">
                [{citation.index}] {citation.author}
              </span>
              <span className="text-xs text-gray-500">on {citation.source}</span>
              {citation.relevance_score !== undefined && (
                <span className="text-xs text-gray-400">
                  ({Math.round(citation.relevance_score * 100)}% relevant)
                </span>
              )}
            </div>

            {/* Quote */}
            {citation.quote && !isExpanded && (
              <div className="mt-2 flex gap-2">
                <Quote className="w-4 h-4 text-gray-400 flex-shrink-0 mt-0.5" />
                <p className="text-sm text-gray-700 italic">{citation.quote}</p>
              </div>
            )}

            {/* URL */}
            {citation.url && (
              <a
                href={citation.url}
                target="_blank"
                rel="noopener noreferrer"
                className="text-xs text-blue-600 hover:underline flex items-center gap-1 mt-1"
                onClick={(e) => e.stopPropagation()}
              >
                View source
                <ExternalLink className="w-3 h-3" />
              </a>
            )}
          </div>
        </div>
      </div>

      {/* Expanded Content */}
      {isExpanded && (
        <div className="border-t border-gray-200 p-3 bg-white">
          {citation.full_content && (
            <div className="space-y-2">
              <h4 className="text-xs font-medium text-gray-700 uppercase">Full Review</h4>
              <div className="text-sm text-gray-800 leading-relaxed whitespace-pre-wrap">
                {citation.full_content}
              </div>
            </div>
          )}

          {citation.date && (
            <p className="text-xs text-gray-500 mt-2">
              <span className="font-medium">Date:</span> {citation.date}
            </p>
          )}
        </div>
      )}
    </div>
  );
};

export const SourceCitations = ({ sources, className = '' }: SourceCitationsProps) => {
  const [isOpen, setIsOpen] = useState(true);

  if (!sources || sources.length === 0) {
    return null;
  }

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
          <h3 className="font-semibold text-gray-900">Sources</h3>
          <span className="text-xs text-gray-500">({sources.length} citations)</span>
        </div>
      </div>

      {/* Source List */}
      {isOpen && (
        <div className="p-4 pt-0 space-y-2 border-t border-gray-100">
          {sources.map((citation) => (
            <SourceItem key={citation.id} citation={citation} />
          ))}
        </div>
      )}
    </div>
  );
};

export default SourceCitations;

