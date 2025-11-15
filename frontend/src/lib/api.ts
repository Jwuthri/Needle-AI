import type { ChatRequest, ChatResponse, ChatSession } from '@/types/chat'

const API_BASE_URL = process.env.NEXT_PUBLIC_API_URL || 'http://localhost:8000/api/v1'

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
    return this.request<ChatResponse>('/chat/', {
      method: 'POST',
      body: JSON.stringify(request),
    })
  }

  async createSession(): Promise<ChatSession> {
    return this.request<ChatSession>('/chat/sessions', {
      method: 'POST',
    })
  }

  async getSession(sessionId: string): Promise<ChatSession> {
    return this.request<ChatSession>(`/chat/sessions/${sessionId}`)
  }

  async listSessions(): Promise<{ sessions: ChatSession[] }> {
    const sessions = await this.request<ChatSession[]>('/chat/sessions')
    return { sessions }
  }

  async deleteSession(sessionId: string): Promise<{ message: string }> {
    return this.request<{ message: string }>(`/chat/sessions/${sessionId}`, {
      method: 'DELETE',
    })
  }

  async healthCheck(): Promise<HealthResponse> {
    return this.request<HealthResponse>('/health/')
  }

  async getRoot(): Promise<{
    message: string
    version: string
    docs: string
    health: string
  }> {
    // Root endpoint is at server root, not under /api/v1
    const baseUrl = this.baseUrl.replace('/api/v1', '')
    const url = `${baseUrl}/`
    const response = await fetch(url)
    if (!response.ok) {
      throw new Error(`HTTP ${response.status}: ${response.statusText}`)
    }
    return response.json()
  }

  // Company endpoints
  async createCompany(data: { name: string; domain: string; industry: string }): Promise<any> {
    return this.request('/companies/', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async listCompanies(): Promise<{ companies: any[] }> {
    return this.request('/companies/')
  }

  async getCompany(id: string): Promise<any> {
    return this.request(`/companies/${id}`)
  }

  async updateCompany(id: string, data: { name?: string; domain?: string; industry?: string }): Promise<any> {
    return this.request(`/companies/${id}`, {
      method: 'PATCH',
      body: JSON.stringify(data),
    })
  }

  async deleteCompany(id: string): Promise<{ message: string }> {
    return this.request(`/companies/${id}`, {
      method: 'DELETE',
    })
  }

  // Scraping endpoints
  async listScrapingSources(): Promise<{ sources: any[] }> {
    return this.request('/scraping/sources')
  }

  async startScrapingJob(data: { 
    company_id: string
    source_id: string
    review_count?: number
    max_cost?: number
    generation_mode?: string
  }): Promise<any> {
    return this.request('/scraping/jobs', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getScrapingJob(id: string): Promise<any> {
    return this.request(`/scraping/jobs/${id}`)
  }

  async listScrapingJobs(companyId?: string): Promise<{ jobs: any[] }> {
    const url = companyId ? `/scraping/jobs?company_id=${companyId}` : '/scraping/jobs'
    return this.request(url)
  }

  async estimateScrapingCost(sourceId: string, totalReviews: number): Promise<any> {
    return this.request('/scraping/estimate', {
      method: 'POST',
      body: JSON.stringify({ source_id: sourceId, total_reviews: totalReviews }),
    })
  }

  // Analytics endpoints
  async getAnalyticsOverview(companyId: string, dateFrom?: string, dateTo?: string): Promise<any> {
    let url = `/analytics/${companyId}/overview`
    const params = new URLSearchParams()
    if (dateFrom) params.append('date_from', dateFrom)
    if (dateTo) params.append('date_to', dateTo)
    const queryString = params.toString()
    if (queryString) url += `?${queryString}`
    return this.request(url)
  }

  async getCompanyInsights(companyId: string): Promise<any> {
    return this.request(`/analytics/${companyId}/insights`)
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
    return this.request(`/analytics/${params.company_id}/reviews?${queryParams.toString()}`)
  }

  // Credits endpoints
  async getCreditBalance(): Promise<any> {
    return this.request('/payments/credits')
  }

  async addFreeCredits(amount: number): Promise<any> {
    return this.request('/payments/credits/free', {
      method: 'POST',
      body: JSON.stringify({ amount }),
    })
  }

  async createCheckoutSession(data: { pricing_tier_id: string; success_url: string; cancel_url: string }): Promise<any> {
    return this.request('/payments/checkout', {
      method: 'POST',
      body: JSON.stringify(data),
    })
  }

  async getCreditTransactions(page?: number, pageSize?: number): Promise<any> {
    const params = new URLSearchParams()
    if (page !== undefined) params.append('page', page.toString())
    if (pageSize !== undefined) params.append('page_size', pageSize.toString())
    const queryString = params.toString()
    const url = queryString ? `/payments/transactions?${queryString}` : '/payments/transactions'
    return this.request(url)
  }

  // Data import endpoints
  async uploadCSV(companyId: string, file: File): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)
    formData.append('company_id', companyId)

    const url = `${this.baseUrl}/data-imports/csv`
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
    return this.request(`/data-imports/${importId}/status`)
  }

  async listDataImports(companyId?: string): Promise<{ imports: any[] }> {
    const url = companyId ? `/data-imports?company_id=${companyId}` : '/data-imports'
    return this.request(url)
  }

  // User dataset endpoints
  async uploadUserDataset(file: File, tableName?: string): Promise<any> {
    const formData = new FormData()
    formData.append('file', file)
    if (tableName) {
      formData.append('table_name', tableName)
    }

    const url = `${this.baseUrl}/user-datasets/upload`
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
      let errorMessage = `HTTP ${response.status}: ${response.statusText}`
      try {
        const errorData = await response.json()
        errorMessage = errorData.detail || errorData.message || errorMessage
      } catch {
        // If we can't parse the error, use the default message
      }
      
      // Create error with status code for better handling
      const error = new Error(errorMessage) as any
      error.status = response.status
      throw error
    }

    return response.json()
  }

  async listUserDatasets(limit?: number, offset?: number): Promise<{ datasets: any[]; total: number }> {
    const params = new URLSearchParams()
    if (limit !== undefined) params.append('limit', limit.toString())
    if (offset !== undefined) params.append('offset', offset.toString())
    const queryString = params.toString()
    const url = queryString ? `/user-datasets?${queryString}` : '/user-datasets'
    return this.request(url)
  }

  async getUserDataset(datasetId: string): Promise<any> {
    return this.request(`/user-datasets/${datasetId}`)
  }

  async getDatasetData(datasetId: string, limit?: number, offset?: number): Promise<any> {
    const params = new URLSearchParams()
    if (limit !== undefined) params.append('limit', limit.toString())
    if (offset !== undefined) params.append('offset', offset.toString())
    const queryString = params.toString()
    const url = queryString ? `/user-datasets/${datasetId}/data?${queryString}` : `/user-datasets/${datasetId}/data`
    return this.request(url)
  }

  async deleteUserDataset(datasetId: string): Promise<{ message: string; dataset_id: string }> {
    return this.request(`/user-datasets/${datasetId}`, {
      method: 'DELETE',
    })
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
