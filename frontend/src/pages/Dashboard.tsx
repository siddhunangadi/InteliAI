import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { formatDistanceToNow } from 'date-fns'
import { Search, Upload, MessageCircle, FileText, ArrowUpRight } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { DocumentsResponse, DiagnosticsResponse } from '@/lib/types'
import { Card, CardSkeleton, Button } from '@/components/ui'

export default function Dashboard() {
  const navigate = useNavigate()
  const [docs, setDocs] = useState<DocumentsResponse | null>(null)
  const [diagnostics, setDiagnostics] = useState<DiagnosticsResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([apiClient.listDocuments(), apiClient.getDiagnostics()])
      .then(([docsData, diagData]) => {
        setDocs(docsData)
        setDiagnostics(diagData)
      })
      .finally(() => setLoading(false))
  }, [])

  const readiness = diagnostics?.readiness ?? []
  const allReady = readiness.length > 0 && readiness.every((c) => c.ok)
  const someDown = readiness.some((c) => !c.ok)

  const stats = [
    { label: 'Regulations', value: docs?.total_documents ?? 0 },
    { label: 'Chunks indexed', value: docs?.total_chunks ?? 0 },
    { label: 'API requests', value: diagnostics?.metrics.request_count ?? 0 },
  ]

  return (
    <div className="space-y-10">
      {/* Hero: the ask-first workspace. Search dominates; stats recede to a
          thin inline strip beneath it (DESIGN.md: ask is the hero, stats a
          supporting player, never the reverse). */}
      <div className="space-y-6">
        <div className="flex items-start justify-between gap-6 flex-wrap">
          <div>
            <h1 className="text-display text-ink">Welcome back</h1>
            <p className="text-ink-muted mt-1.5">
              {docs?.total_documents
                ? `${docs.total_documents} regulation${docs.total_documents !== 1 ? 's' : ''} indexed and searchable.`
                : 'Upload your first regulation to get started.'}
            </p>
          </div>
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-sm border text-label ${
              readiness.length === 0
                ? 'border-seam text-ink-muted bg-panel'
                : allReady
                ? 'border-status-verified/30 text-status-verified bg-status-verified/10'
                : 'border-status-critical/30 text-status-critical bg-status-critical/10'
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${allReady ? 'bg-status-verified' : someDown ? 'bg-status-critical' : 'bg-ink-muted'}`} />
            {readiness.length === 0 ? 'Diagnostics unavailable' : allReady ? 'All systems operational' : 'Degraded'}
          </div>
        </div>

        {/* Ask -- the primary action on this screen */}
        <button
          onClick={() => navigate('/chat')}
          className="w-full text-left card p-6 hover:bg-panel-raised transition-colors group"
        >
          <div className="flex items-center gap-3">
            <MessageCircle className="w-5 h-5 text-signal flex-shrink-0" />
            <span className="text-title text-ink-muted group-hover:text-ink transition-colors">
              Ask a question about your regulations, policies, or filings...
            </span>
          </div>
        </button>

        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-ink-muted" />
            <input
              type="text"
              placeholder="Search regulations, circulars, or acts..."
              className="input pl-10"
              onClick={() => navigate('/regulations')}
              readOnly
            />
          </div>
          <Button onClick={() => navigate('/upload')} variant="secondary" icon={<Upload className="w-4 h-4" />}>
            Upload
          </Button>
        </div>

        {/* Inline stat strip -- not cards */}
        <div className="flex items-center gap-8 flex-wrap">
          {stats.map((s, i) => (
            <div key={s.label} className={`flex items-baseline gap-2 ${i > 0 ? 'pl-8 border-l border-seam' : ''}`}>
              <span className="text-2xl font-semibold tracking-tighter tabular-nums text-ink">{loading ? '—' : s.value}</span>
              <span className="text-label text-ink-muted">{s.label}</span>
            </div>
          ))}
        </div>
      </div>

      {/* Recent activity */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-title text-ink">Recent Activity</h2>
          <button
            onClick={() => navigate('/regulations')}
            className="text-label text-ink-muted hover:text-ink transition-colors flex items-center gap-1"
          >
            View all <ArrowUpRight className="w-3 h-3" />
          </button>
        </div>

        {loading ? (
          <div className="space-y-3">
            {Array.from({ length: 3 }).map((_, i) => <CardSkeleton key={i} />)}
          </div>
        ) : docs?.documents?.length ? (
          <Card className="p-0 overflow-hidden">
            <div className="divide-y divide-seam">
              {docs.documents.slice(0, 6).map((doc) => (
                <button
                  key={doc.document_id}
                  onClick={() => navigate('/regulations')}
                  className="w-full flex items-center gap-4 p-4 hover:bg-panel-raised transition-colors text-left group"
                >
                  <div className="w-9 h-9 rounded-sm bg-panel-raised border border-seam flex items-center justify-center flex-shrink-0">
                    <FileText className="w-4 h-4 text-ink-muted" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate text-ink">{doc.filename}</p>
                    <p className="text-label text-ink-muted mt-0.5">{doc.chunk_count} chunks indexed</p>
                  </div>
                  <span className="text-label text-ink-muted whitespace-nowrap">
                    {doc.indexed_at ? formatDistanceToNow(new Date(doc.indexed_at), { addSuffix: true }) : ''}
                  </span>
                  <ArrowUpRight className="w-3.5 h-3.5 text-ink-muted group-hover:text-ink transition-colors flex-shrink-0" />
                </button>
              ))}
            </div>
          </Card>
        ) : (
          <Card>
            <p className="text-sm text-ink-muted py-6 text-center">No regulations uploaded yet.</p>
          </Card>
        )}
      </div>
    </div>
  )
}
