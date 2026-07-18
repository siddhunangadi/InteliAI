import { DiagnosticsResponse } from '@/lib/types'
import { Card } from '@/components/ui'

interface DiagnosticsPanelProps {
  diagnostics: DiagnosticsResponse | null
  loading: boolean
}

export default function DiagnosticsPanel({ diagnostics, loading }: DiagnosticsPanelProps) {
  if (loading) return <div className="h-40 bg-paper-raised rounded-md" />

  if (!diagnostics) return <Card>No diagnostic data available</Card>

  const getReadinessStatus = (name: string): boolean => {
    return diagnostics.readiness.find(r => r.name === name)?.ok ?? false
  }

  return (
    <div className="space-y-4">
      <Card>
        <h3 className="text-title text-ink mb-3">System Information</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-ink-muted">Build</span>
            <span className="text-mono-data text-ink">{diagnostics.build.name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-muted">Version</span>
            <span className="text-mono-data text-ink">{diagnostics.build.version}</span>
          </div>
        </div>
      </Card>

      <Card>
        <h3 className="text-title text-ink mb-3">Service Providers</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-ink-muted">Generation Provider</span>
            <span className="text-mono-data text-ink">{diagnostics.providers.generation}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-muted">Embedding Provider</span>
            <span className="text-mono-data text-ink">{diagnostics.providers.embedding}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-muted">Reranking Backend</span>
            <span className="text-mono-data text-ink">{diagnostics.providers.rerank_backend}</span>
          </div>
        </div>
      </Card>

      <Card>
        <h3 className="text-title text-ink mb-3">Service Status</h3>
        <div className="space-y-2 text-sm">
          {[
            ['Vector Search', 'pinecone'],
            ['Full-Text Search', 'bm25'],
            ['Embeddings', 'embedding_provider'],
            ['Audit Logging', 'audit'],
          ].map(([label, key]) => {
            const ready = getReadinessStatus(key)
            return (
              <div key={key} className="flex justify-between">
                <span className="text-ink-muted">{label}</span>
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${ready ? 'bg-status-verified' : 'bg-status-critical'}`} />
                  <span className={ready ? 'text-status-verified' : 'text-status-critical'}>
                    {ready ? 'Ready' : 'Down'}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </Card>

      <Card>
        <h3 className="text-title text-ink mb-3">Performance Metrics</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-ink-muted">Requests</span>
            <span className="text-ink">{diagnostics.metrics.request_count}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-muted">Avg Response Time</span>
            <span className="text-ink">{Math.round(diagnostics.metrics.avg_latency_ms)}ms</span>
          </div>
        </div>
      </Card>

      <Card>
        <h3 className="text-title text-ink mb-3">Ingestion Stats</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-ink-muted">Total Documents</span>
            <span className="text-ink">{diagnostics.ingestion_stats.total_documents}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-ink-muted">Total Chunks</span>
            <span className="text-ink">{diagnostics.ingestion_stats.total_chunks}</span>
          </div>
        </div>
      </Card>

      <Card>
        <h3 className="text-title text-ink mb-3">Audit Stats</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-ink-muted">Total Events</span>
            <span className="text-ink">{diagnostics.audit_stats.total_events}</span>
          </div>
        </div>
      </Card>
    </div>
  )
}
