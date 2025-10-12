export interface AnalyticsOverview {
  total_reviews: number;
  reviews_by_source: Record<string, number>;
  sentiment_distribution: {
    positive: number;
    neutral: number;
    negative: number;
  };
  date_range: {
    start: string;
    end: string;
  };
}

export interface CompanyInsights {
  common_themes: string[];
  product_gaps: string[];
  top_competitors: string[];
  top_feature_requests: string[];
  summary?: string;
}

export interface ReviewsListParams {
  company_id: string;
  page?: number;
  page_size?: number;
  source?: string;
  sentiment?: 'positive' | 'neutral' | 'negative';
  date_from?: string;
  date_to?: string;
  search?: string;
}

export interface ReviewsListResponse {
  reviews: Array<{
    id: string;
    content: string;
    author: string;
    source: string;
    sentiment_score: number;
    url?: string;
    scraped_at: string;
  }>;
  total: number;
  page: number;
  page_size: number;
  total_pages: number;
}

export interface SentimentTrend {
  date: string;
  positive: number;
  neutral: number;
  negative: number;
  total: number;
}

