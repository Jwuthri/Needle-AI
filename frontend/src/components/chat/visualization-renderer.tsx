'use client';

import { useEffect, useRef } from 'react';
import { BarChart3, LineChart, PieChart, Table as TableIcon } from 'lucide-react';

interface ChartConfig {
  type: 'bar' | 'line' | 'pie' | 'table';
  title?: string;
  data: {
    labels?: string[];
    datasets?: Array<{
      label?: string;
      data: number[];
      backgroundColor?: string | string[];
      borderColor?: string | string[];
      borderWidth?: number;
      fill?: boolean;
      tension?: number;
    }>;
  };
  options?: any;
  columns?: string[];
  rows?: Array<Record<string, any>>;
  totalRows?: number;
}

interface VisualizationRendererProps {
  config: ChartConfig;
  className?: string;
}

const TableVisualization = ({ config }: { config: ChartConfig }) => {
  const columns = config.columns || [];
  const rows = config.rows || [];

  return (
    <div className="overflow-x-auto">
      <table className="min-w-full divide-y divide-gray-200 border border-gray-200 rounded-lg">
        <thead className="bg-gray-50">
          <tr>
            {columns.map((col, idx) => (
              <th
                key={idx}
                className="px-4 py-3 text-left text-xs font-medium text-gray-700 uppercase tracking-wider"
              >
                {col}
              </th>
            ))}
          </tr>
        </thead>
        <tbody className="bg-white divide-y divide-gray-200">
          {rows.map((row, rowIdx) => (
            <tr key={rowIdx} className="hover:bg-gray-50">
              {columns.map((col, colIdx) => (
                <td key={colIdx} className="px-4 py-3 text-sm text-gray-900">
                  {String(row[col] ?? '-')}
                </td>
              ))}
            </tr>
          ))}
        </tbody>
      </table>
      {config.totalRows && config.totalRows > rows.length && (
        <p className="text-xs text-gray-500 mt-2 text-center">
          Showing {rows.length} of {config.totalRows} rows
        </p>
      )}
    </div>
  );
};

const ChartVisualization = ({ config }: { config: ChartConfig }) => {
  const canvasRef = useRef<HTMLCanvasElement>(null);
  const chartRef = useRef<any>(null);

  useEffect(() => {
    const loadChartJS = async () => {
      if (!canvasRef.current) return;

      try {
        // Dynamically import Chart.js
        const { Chart, registerables } = await import('chart.js');
        Chart.register(...registerables);

        // Destroy existing chart
        if (chartRef.current) {
          chartRef.current.destroy();
        }

        // Create new chart
        const ctx = canvasRef.current.getContext('2d');
        if (ctx) {
          chartRef.current = new Chart(ctx, {
            type: config.type,
            data: config.data,
            options: {
              responsive: true,
              maintainAspectRatio: true,
              plugins: {
                legend: {
                  display: true,
                  position: 'top',
                },
                title: {
                  display: !!config.title,
                  text: config.title,
                },
              },
              ...config.options,
            },
          });
        }
      } catch (error) {
        console.error('Failed to load Chart.js:', error);
      }
    };

    loadChartJS();

    return () => {
      if (chartRef.current) {
        chartRef.current.destroy();
      }
    };
  }, [config]);

  return (
    <div className="relative w-full" style={{ height: '400px' }}>
      <canvas ref={canvasRef} />
    </div>
  );
};

const getChartIcon = (type: string) => {
  switch (type) {
    case 'bar':
      return <BarChart3 className="w-5 h-5" />;
    case 'line':
      return <LineChart className="w-5 h-5" />;
    case 'pie':
      return <PieChart className="w-5 h-5" />;
    case 'table':
      return <TableIcon className="w-5 h-5" />;
    default:
      return <BarChart3 className="w-5 h-5" />;
  }
};

export const VisualizationRenderer = ({ config, className = '' }: VisualizationRendererProps) => {
  if (!config) {
    return null;
  }

  return (
    <div className={`border border-gray-200 rounded-lg bg-white p-4 ${className}`}>
      {/* Header */}
      <div className="flex items-center gap-2 mb-4">
        <div className="text-gray-600">{getChartIcon(config.type)}</div>
        {config.title && <h3 className="font-semibold text-gray-900">{config.title}</h3>}
        <span className="text-xs text-gray-500 capitalize ml-auto">
          {config.type} {config.type === 'table' ? '' : 'chart'}
        </span>
      </div>

      {/* Visualization */}
      <div className="mt-2">
        {config.type === 'table' ? (
          <TableVisualization config={config} />
        ) : (
          <ChartVisualization config={config} />
        )}
      </div>
    </div>
  );
};

export default VisualizationRenderer;

