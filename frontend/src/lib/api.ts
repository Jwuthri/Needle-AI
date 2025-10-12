const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000'

export interface ChatRequest {
  message: string
  session_id?: string
  context?: Record<string, any>
}

export interface ChatResponse {
  message: string
  session_id: string
  message_id: string
  timestamp: string
  metadata?: Record<string, any>
}

export interface ChatSession {
  session_id: string
  messages: Array<{
    id: string
    content: string
    role: 'user' | 'assistant' | 'system'
    timestamp: string
  }>
}

export interface HealthResponse {
  status: 'healthy' | 'unhealthy'
  timestamp: string
  service: string
  version?: string
}

class ApiClient {
  private baseUrl: string
  private token?: string | null

  constructor(baseUrl: string = API_BASE_URL, token?: string | null) {
    this.baseUrl = baseUrl.replace(/\/$/, '') // Remove trailing slash
    this.token = token
  }

  private async request<T>(
    endpoint: string,
    options: RequestInit = {}
  ): Promise<T> {
    const url = `${this.baseUrl}${endpoint}`

    const headers: Record<string, string> = {
      'Content-Type': 'application/json',
      ...(options.headers as Record<string, string>),
    }

    // Add authentication header if token is available
    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`
    }

    const config: RequestInit = {
      headers,
      ...options,
    }

    try {
      const response = await fetch(url, config)

      if (!response.ok) {
        let errorMessage = `HTTP ${response.status}: ${response.statusText}`

        try {
          const errorData = await response.json()
          errorMessage = errorData.detail || errorData.message || errorMessage
        } catch {
          // If we can't parse the error, use the default message
        }

        throw new Error(errorMessage)
      }

      // Handle empty responses
      const contentType = response.headers.get('content-type')
      if (contentType && contentType.includes('application/json')) {
        return await response.json()
      } else {
        return response.text() as unknown as T
      }
    } catch (error) {
      if (error instanceof Error) {
        throw error
      }
      throw new Error('An unexpected error occurred')
    }
  }

  async sendMessage(request: ChatRequest): Promise<ChatResponse> {
    return this.request<ChatResponse>('/api/v1/chat/', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async getSession(sessionId: string): Promise<ChatSession> {
    return this.request<ChatSession>(`/api/v1/chat/sessions/${sessionId}`)
  }

  async listSessions(): Promise<{ sessions: Array<{ session_id: string; message_count: number; last_activity: string | null }> }> {
    return this.request<{ sessions: Array<{ session_id: string; message_count: number; last_activity: string | null }> }>('/api/v1/chat/sessions')
  }

  async deleteSession(sessionId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/api/v1/chat/sessions/${sessionId}`, {
      method: 'DELETE',
    })
  }

  async healthCheck(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/api/v1/health/')
  }

  async getRoot(): Promise<{
    message: string
    version: string
    docs: string
    health: string
  }> {
    return this.request<{
      message: string
      version: string
      docs: string
      health: string
    }>('/')
  }

  // Company endpoints
  async createCompany(data: { name: string; domain: string; industry: string }): Promise<any> {
    return this.request('/api/v1/companies/', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async listCompanies(): Promise<{ companies: any[] }> {
    return this.request('/api/v1/companies/')
  }

  async getCompany(id: string): Promise<any> {
    return this.request(`/api/v1/companies/${id}`)
  }

  async updateCompany(id: string, data: { name?: string; domain?: string; industry?: string }): Promise<any> {
    return this.request(`/api/v1/companies/${id}`, {
      method: 'PUT',
      body: JSON.stringify(data),
    })
  }

  async deleteCompany(id: string): Promise<{ message: string }> {
    return this.request(`/api/v1/companies/${id}`, {
      method: 'DELETE',
    })
  }

  // Scraping endpoints
  async listScrapingSources(): Promise<{ sources: any[] }> {
    return this.request('/api/v1/scraping/sources')
  }

  async startScrapingJob(data: { company_id: string; source_id: string; total_reviews_target: number }): Promise<any> {
    return this.request('/api/v1/scraping/jobs', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getScrapingJob(id: string): Promise<any> {
    return this.request(`/api/v1/scraping/jobs/${id}`)
  }

  async listScrapingJobs(companyId?: string): Promise<{ jobs: any[] }> {
    const url = companyId ? `/api/v1/scraping/jobs?company_id=${companyId}` : '/api/v1/scraping/jobs'
    return this.request(url)
  }

  async estimateScrapingCost(sourceId: string, totalReviews: number): Promise<any> {
    return this.request('/api/v1/scraping/estimate', {
      method: 'POST',
      body: JSON.stringify({ source_id: sourceId, total_reviews: totalReviews }),
    })
  }

  // Analytics endpoints
  async getAnalyticsOverview(companyId: string, dateFrom?: string, dateTo?: string): Promise<any> {
    let url = `/api/v1/analytics/${companyId}/overview`
    const params = new URLSearchParams()
    if (dateFrom) params.append('date_from', dateFrom)
    if (dateTo) params.append('date_to', dateTo)
    const queryString = params.toString()
    if (queryString) url += `?${queryString}`
    return this.request(url)
  }

  async getCompanyInsights(companyId: string): Promise<any> {
    return this.request(`/api/v1/analytics/${companyId}/insights`)
  }

  async getReviews(params: {
    company_id: string
    page?: number
    page_size?: number
    source?: string
    sentiment?: string
    date_from?: string
    date_to?: string
    search?: string
  }): Promise<any> {
    const queryParams = new URLSearchParams()
    Object.entries(params).forEach(([key, value]) => {
      if (value !== undefined) queryParams.append(key, value.toString())
    })
    return this.request(`/api/v1/analytics/${params.company_id}/reviews?${queryParams.toString()}`)
  }

  // Credits endpoints
  async getCreditBalance(): Promise<any> {
    return this.request('/api/v1/payments/credits')
  }

  async createCheckoutSession(data: { pricing_tier_id: string; success_url: string; cancel_url: string }): Promise<any> {
    return this.request('/api/v1/payments/checkout', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getCreditTransactions(page?: number, pageSize?: number): Promise<any> {
    const params = new URLSearchParams()
    if (page !== undefined) params.append('page', page.toString())
    if (pageSize !== undefined) params.append('page_size', pageSize.toString())
    const queryString = params.toString()
    const url = queryString ? `/api/v1/payments/transactions?${queryString}` : '/api/v1/payments/transactions'
    return this.request(url)
  }

  // Data import endpoints
  async uploadCSV(companyId: string, file: File): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('company_id', companyId)

    const url = `${this.baseUrl}/api/v1/data-imports/csv`
    const headers: Record<string, string> = {}
    if (this.token) {
      headers.Authorization = `Bearer ${this.token}`
    }

    const response = await fetch(url, {
      method: 'POST',
      headers,
      body: formData,
    })

    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }

    return response.json()
  }

  async getDataImportStatus(importId: string): Promise<any> {
    return this.request(`/api/v1/data-imports/${importId}/status`)
  }

  async listDataImports(companyId?: string): Promise<{ imports: any[] }> {
    const url = companyId ? `/api/v1/data-imports?company_id=${companyId}` : '/api/v1/data-imports'
    return this.request(url)
  }
}

// Default unauthenticated client (for public endpoints)
export const apiClient = new ApiClient()

// Factory function to create authenticated API client
export const createApiClient = (token?: string | null): ApiClient => {
  return new ApiClient(API_BASE_URL, token)
}

// WebSocket client for real-time communication
export class WebSocketClient {
  private ws: WebSocket | null = null
  private baseUrl: string
  private sessionId: string
  private messageHandlers: Array<(data: any) => void> = []
  private connectionHandlers: Array<(connected: boolean) => void> = []

  constructor(sessionId: string, baseUrl: string = process.env.NEXT_PUBLIC_WS_URL || 'ws://localhost:8000') {
    this.baseUrl = baseUrl.replace(/\/$/, '')
    this.sessionId = sessionId
  }

  connect() {
    if (this.ws?.readyState === WebSocket.OPEN) {
      return
    }

    try {
      const wsUrl = `${this.baseUrl}/ws/${this.sessionId}`
      this.ws = new WebSocket(wsUrl)

      this.ws.onopen = () => {
        console.log('WebSocket connected')
        this.connectionHandlers.forEach(handler => handler(true))
      }

      this.ws.onmessage = (event) => {
        try {
          const data = JSON.parse(event.data)
          this.messageHandlers.forEach(handler => handler(data))
        } catch (error) {
          console.error('Error parsing WebSocket message:', error)
        }
      }

      this.ws.onclose = () => {
        console.log('WebSocket disconnected')
        this.connectionHandlers.forEach(handler => handler(false))
      }

      this.ws.onerror = (error) => {
        console.error('WebSocket error:', error)
        this.connectionHandlers.forEach(handler => handler(false))
      }
    } catch (error) {
      console.error('Error creating WebSocket connection:', error)
    }
  }

  disconnect() {
    if (this.ws) {
      this.ws.close()
      this.ws = null
    }
  }

  sendMessage(message: string) {
    if (this.ws?.readyState === WebSocket.OPEN) {
      this.ws.send(JSON.stringify({ message }))
    } else {
      throw new Error('WebSocket is not connected')
    }
  }

  onMessage(handler: (data: any) => void) {
    this.messageHandlers.push(handler)
  }

  onConnection(handler: (connected: boolean) => void) {
    this.connectionHandlers.push(handler)
  }

  removeMessageHandler(handler: (data: any) => void) {
    const index = this.messageHandlers.indexOf(handler)
    if (index > -1) {
      this.messageHandlers.splice(index, 1)
    }
  }

  removeConnectionHandler(handler: (connected: boolean) => void) {
    const index = this.connectionHandlers.indexOf(handler)
    if (index > -1) {
      this.connectionHandlers.splice(index, 1)
    }
  }

  isConnected(): boolean {
    return this.ws?.readyState === WebSocket.OPEN
  }
}
