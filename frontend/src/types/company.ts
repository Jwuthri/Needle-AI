export interface ReviewUrls {
  g2?: string;
  trustpilot?: string;
  trustradius?: string;
}

export interface Company {
  id: string;
  name: string;
  domain: string;
  industry: string;
  created_at: string;
  updated_at?: string;
  total_reviews?: number;
  last_scrape?: string;
  user_id: string;
  review_urls?: ReviewUrls;
}

export interface CreateCompanyRequest {
  name: string;
  domain: string;
  industry: string;
}

export interface UpdateCompanyRequest {
  name?: string;
  domain?: string;
  industry?: string;
}

