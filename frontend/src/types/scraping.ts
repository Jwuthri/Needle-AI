export interface ScrapingSource {
  id: string;
  name: string;
  source_type: 'reddit' | 'twitter' | 'custom';
  cost_per_review: number;
  is_active: boolean;
  description?: string;
  icon?: string;
}

export interface ScrapingJob {
  id: string;
  company_id: string;
  source_id: string;
  status: 'pending' | 'running' | 'completed' | 'failed';
  progress_percentage: number;
  total_reviews_target: number;
  reviews_fetched: number;
  cost: number;
  started_at?: string;
  completed_at?: string;
  created_at?: string;
  error_message?: string;
  user_id: string;
  // Human-readable names
  source_name?: string;
  company_name?: string;
}

export interface StartScrapingJobRequest {
  company_id: string;
  source_id: string;
  total_reviews_target: number;
}

export interface ScrapingJobEstimate {
  estimated_cost: number;
  estimated_duration_minutes: number;
  source_name: string;
}

export interface Review {
  id: string;
  company_id: string;
  source_id: string;
  scraping_job_id?: string;
  content: string;
  author: string;
  sentiment_score: number;
  url?: string;
  metadata?: Record<string, any>;
  scraped_at: string;
  processed_at?: string;
}

export interface DataImport {
  id: string;
  company_id: string;
  user_id: string;
  file_path: string;
  import_type: 'csv' | 'json';
  status: 'pending' | 'processing' | 'completed' | 'failed';
  rows_imported: number;
  total_rows?: number;
  created_at: string;
  completed_at?: string;
  error_message?: string;
}

