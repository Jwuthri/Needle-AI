export interface UserCredit {
  id: string;
  user_id: string;
  credits_available: number;
  total_purchased: number;
  stripe_customer_id?: string;
  last_purchase_at?: string;
}

export interface CreditTransaction {
  id: string;
  user_id: string;
  amount: number;
  type: 'purchase' | 'usage' | 'refund';
  description: string;
  balance_after: number;
  created_at: string;
  metadata?: Record<string, any>;
}

export interface PricingTier {
  id: string;
  name: string;
  credits: number;
  price: number;
  price_per_credit: number;
  popular?: boolean;
  savings?: string;
}

export interface CheckoutSessionRequest {
  pricing_tier_id: string;
  success_url: string;
  cancel_url: string;
}

export interface CheckoutSessionResponse {
  session_id: string;
  url: string;
}

