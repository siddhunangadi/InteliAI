/// <reference types="vite/client" />
import axios, { AxiosInstance } from 'axios'
import * as Types from './types'

// Production serves frontend and API from the same origin (see Dockerfile /
// api/main.py), so the safe default there is a relative baseURL. Local `vite
// dev` runs on a separate port from the backend, so it still needs an
// absolute default unless VITE_API_URL is set explicitly.
const BASE_URL = import.meta.env.VITE_API_URL || (import.meta.env.DEV ? 'http://localhost:8000' : '')

class ApiClient {
  private client: AxiosInstance

  constructor() {
    this.client = axios.create({
      baseURL: BASE_URL,
      headers: {
        'Content-Type': 'application/json',
      },
    })
    // Read fresh on every request (not just once at construction) so saving
    // a new key in Settings takes effect without a page reload. Backend
    // requires this exact header name (see api/auth.py get_identity).
    this.client.interceptors.request.use(config => {
      const apiKey = localStorage.getItem('apiKey')
      if (apiKey) config.headers['X-API-Key'] = apiKey
      return config
    })
  }

  // Health
  async getHealth(): Promise<Types.HealthResponse> {
    const { data } = await this.client.get('/health')
    return data
  }

  async getLiveness(): Promise<Types.LivenessResponse> {
    const { data } = await this.client.get('/health/live')
    return data
  }

  async getReadiness(): Promise<Types.ReadinessResponse> {
    const { data } = await this.client.get('/health/ready')
    return data
  }

  // Documents
  async listDocuments(): Promise<Types.DocumentsResponse> {
    const { data } = await this.client.get('/documents')
    return data
  }

  async getDocument(documentId: string): Promise<Types.DocumentDetail> {
    const { data } = await this.client.get(`/documents/${documentId}`)
    return data
  }

  async deleteDocument(documentId: string): Promise<void> {
    await this.client.delete(`/documents/${documentId}`)
  }

  async extractMetadata(file: File): Promise<Types.MetadataExtractionResponse> {
    const formData = new FormData()
    formData.append('file', file)

    const { data } = await this.client.post('/upload/extract-metadata', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  }

  async uploadDocuments(files: File[], metadata: Record<string, unknown>): Promise<Types.JobStatusResponse> {
    const formData = new FormData()
    files.forEach((file) => formData.append('files', file))
    Object.entries(metadata).forEach(([key, value]) => {
      formData.append(key, String(value))
    })

    const { data } = await this.client.post('/upload', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  }

  async uploadDocumentsAsync(files: File[], metadata: Record<string, unknown>): Promise<Types.UploadAcceptedResponse> {
    const formData = new FormData()
    files.forEach((file) => formData.append('files', file))
    Object.entries(metadata).forEach(([key, value]) => {
      if (value) formData.append(key, String(value))
    })

    const { data } = await this.client.post('/upload/async', formData, {
      headers: { 'Content-Type': 'multipart/form-data' },
    })
    return data
  }

  // Chat
  async answer(request: Types.AnswerRequest): Promise<Types.RagAnswer> {
    const { data } = await this.client.post('/answer', request)
    return data
  }

  async *answerStream(request: Types.AnswerRequest): AsyncGenerator<string> {
    // axios's `responseType: 'stream'` only yields a Web ReadableStream in
    // Node; in the browser response.data has no .getReader(). SSE needs a
    // real fetch() response.body here instead.
    const apiKey = localStorage.getItem('apiKey')
    const response = await fetch(`${BASE_URL}/answer/stream`, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(apiKey ? { 'X-API-Key': apiKey } : {}),
      },
      body: JSON.stringify(request),
    })
    if (!response.ok || !response.body) {
      throw new Error(`Stream request failed: ${response.status}`)
    }
    const reader = response.body.getReader()
    const decoder = new TextDecoder()

    try {
      while (true) {
        const { done, value } = await reader.read()
        if (done) break
        yield decoder.decode(value, { stream: true })
      }
    } finally {
      reader.releaseLock()
    }
  }

  // Jobs
  async getJobStatus(jobId: string): Promise<Types.JobStatusResponse> {
    const { data } = await this.client.get(`/jobs/${jobId}`)
    return data
  }

  // Audit
  async getAuditEvents(params: {
    limit?: number
    offset?: number
    event_type?: string
    status?: string
    role?: string
  } = {}): Promise<Types.AuditEventsResponse> {
    const { data } = await this.client.get('/audit/events', {
      params: { limit: 100, offset: 0, ...params },
    })
    return data
  }

  // Diagnostics
  async getDiagnostics(): Promise<Types.DiagnosticsResponse> {
    const { data } = await this.client.get('/diagnostics')
    return data
  }

  // Version
  async getVersion(): Promise<{ version: string }> {
    const { data } = await this.client.get('/version')
    return data
  }
}

export const apiClient = new ApiClient()
