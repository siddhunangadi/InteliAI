// API Response Types

export interface HealthResponse {
  status: 'ok' | 'degraded' | 'error'
  generation_provider: string
  embedding_provider: string
  data_dir: string
}

export interface ComponentStatus {
  name: string
  ok: boolean
  detail?: string | null
}

export interface ReadinessResponse {
  status: 'ready' | 'not_ready'
  checks: ComponentStatus[]
}

export interface MetricsResponse {
  counts: Record<string, number>
  avg_latency_ms: number
  request_count: number
}

export interface DiagnosticsResponse {
  build: {
    name: string
    version: string
  }
  providers: {
    generation: string
    embedding: string
    rerank_backend: string
  }
  readiness: ComponentStatus[]
  config: Record<string, unknown>
  ingestion_stats: {
    total_documents: number
    total_chunks: number
  }
  audit_stats: {
    total_events: number
  }
  metrics: MetricsResponse
}

export interface DocumentSummary {
  document_id: string
  filename: string
  chunk_count: number
}

export interface DocumentsResponse {
  total_documents: number
  total_chunks: number
  documents: DocumentSummary[]
}

export interface AnswerRequest {
  question: string
  top_k?: number
  metadata_filters?: Record<string, unknown>
}

export interface StructuredCitation {
  citation_id: string
  document_id: string
  document_title: string
  chunk_id: string
  confidence: number
  display: string
  regulation: string | null
  version: string | null
  jurisdiction: string | null
  article: string | null
  section: string | null
  clause: string | null
  effective_date: string | null
  document_type: string | null
  page: number | null
}

export interface ConfidenceMetrics {
  retrieval: number
  citations: number
  coverage: number
  overall: number
}

export interface VerificationStats {
  total_claims: number
  verified_claims: number
  failed_claims: number
}

export interface RagAnswer {
  answer: string
  citations: StructuredCitation[]
  structured_citations: StructuredCitation[]
  confidence: ConfidenceMetrics
  verification: VerificationStats
}

export interface AuditEvent {
  event_id: string
  event_type: string
  timestamp: string
  request_id: string
  key_id: string
  role: string | null
  endpoint: string
  action: string
  status: 'success' | 'failure'
  duration_ms?: number | null
  error?: string | null
  metadata?: Record<string, unknown>
}

export interface AuditEventsResponse {
  events: AuditEvent[]
  total: number
  offset: number
  limit: number
}

export interface JobStatusResponse {
  job_id: string
  status: 'processing' | 'ready' | 'failed'
  result?: { results: { filename: string; status: string; error: string | null }[] }
  error?: string | null
}

export interface UploadAcceptedResponse {
  job_id: string
  status: 'processing'
}

export interface LivenessResponse {
  status: 'ok'
  timestamp: string
}
