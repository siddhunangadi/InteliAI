import { DiagnosticsResponse } from '@/lib/types'
import { Card } from '@/components/ui'

interface DiagnosticsPanelProps {
  diagnostics: DiagnosticsResponse | null
  loading: boolean
}

export default function DiagnosticsPanel({ diagnostics, loading }: DiagnosticsPanelProps) {
  if (loading) return <div className="h-40 bg-slate-800/50 rounded animate-pulse" />

  if (!diagnostics) return <Card>No diagnostic data available</Card>

  const getReadinessStatus = (name: string): boolean => {
    return diagnostics.readiness.find(r => r.name === name)?.ok ?? false
  }

  return (
    <div className="space-y-4">
      <Card>
        <h3 className="font-semibold mb-3">System Information</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-400">Build</span>
            <span className="text-white font-mono">{diagnostics.build.name}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Version</span>
            <span className="text-white font-mono">{diagnostics.build.version}</span>
          </div>
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-3">Service Providers</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-400">Generation Provider</span>
            <span className="text-white font-mono">{diagnostics.providers.generation}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Embedding Provider</span>
            <span className="text-white font-mono">{diagnostics.providers.embedding}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Reranking Backend</span>
            <span className="text-white font-mono">{diagnostics.providers.rerank_backend}</span>
          </div>
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-3">Service Status</h3>
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
                <span className="text-slate-400">{label}</span>
                <div className="flex items-center gap-2">
                  <div className={`w-2 h-2 rounded-full ${ready ? 'bg-emerald-400' : 'bg-red-400'}`} />
                  <span className={ready ? 'text-emerald-400' : 'text-red-400'}>
                    {ready ? 'Ready' : 'Down'}
                  </span>
                </div>
              </div>
            )
          })}
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-3">Performance Metrics</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-400">Requests</span>
            <span className="text-white">{diagnostics.metrics.request_count}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Avg Response Time</span>
            <span className="text-white">{Math.round(diagnostics.metrics.avg_latency_ms)}ms</span>
          </div>
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-3">Ingestion Stats</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-400">Total Documents</span>
            <span className="text-white">{diagnostics.ingestion_stats.total_documents}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Total Chunks</span>
            <span className="text-white">{diagnostics.ingestion_stats.total_chunks}</span>
          </div>
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-3">Audit Stats</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-400">Total Events</span>
            <span className="text-white">{diagnostics.audit_stats.total_events}</span>
          </div>
        </div>
      </Card>
    </div>
  )
}
