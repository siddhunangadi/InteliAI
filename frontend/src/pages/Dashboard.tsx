import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
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
  const allReady = readiness.length > 0 && readiness.every(c => c.ok)
  const someDown = readiness.some(c => !c.ok)

  const stats = [
    { label: 'Regulations', value: docs?.total_documents ?? 0 },
    { label: 'Chunks indexed', value: docs?.total_chunks ?? 0 },
    { label: 'API requests', value: diagnostics?.metrics.request_count ?? 0 },
  ]

  return (
    <div className="space-y-10">
      {/* Hero */}
      <motion.div initial={{ opacity: 0, y: -12 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
        <div className="flex items-start justify-between gap-6 flex-wrap">
          <div>
            <h1 className="text-4xl font-semibold tracking-tighter">Welcome back</h1>
            <p className="text-slate-400 mt-1.5">
              {docs?.total_documents
                ? `${docs.total_documents} regulation${docs.total_documents !== 1 ? 's' : ''} indexed and searchable.`
                : 'Upload your first regulation to get started.'}
            </p>
          </div>
          <div
            className={`flex items-center gap-2 px-3 py-1.5 rounded-full border text-sm font-medium ${
              readiness.length === 0
                ? 'border-slate-700 text-slate-400 bg-slate-800/50'
                : allReady
                ? 'border-emerald-500/30 text-emerald-400 bg-emerald-500/10'
                : 'border-red-500/30 text-red-400 bg-red-500/10'
            }`}
          >
            <span className={`w-1.5 h-1.5 rounded-full ${allReady ? 'bg-emerald-400' : someDown ? 'bg-red-400' : 'bg-slate-500'}`} />
            {readiness.length === 0 ? 'Diagnostics unavailable' : allReady ? 'All systems operational' : 'Degraded'}
          </div>
        </div>

        {/* Inline stat strip -- not cards */}
        <div className="flex items-center gap-8 flex-wrap">
          {stats.map((s, i) => (
            <div key={s.label} className={`flex items-baseline gap-2 ${i > 0 ? 'pl-8 border-l border-slate-800' : ''}`}>
              <span className="text-2xl font-semibold tracking-tighter tabular-nums">{loading ? '—' : s.value}</span>
              <span className="text-sm text-slate-400">{s.label}</span>
            </div>
          ))}
        </div>

        {/* Search & Actions */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3.5 top-1/2 -translate-y-1/2 w-4 h-4 text-slate-500" />
            <input
              type="text"
              placeholder="Search regulations, circulars, or acts..."
              className="w-full pl-10 pr-4 py-2.5 bg-slate-900/60 border border-slate-800 rounded-xl text-slate-300 placeholder-slate-500 focus:outline-none focus:ring-2 focus:ring-blue-500/40 focus:border-blue-500/50 transition-all"
              onClick={() => navigate('/regulations')}
              readOnly
            />
          </div>
          <Button onClick={() => navigate('/chat')} className="flex items-center gap-2">
            <MessageCircle className="w-4 h-4" />
            Ask AI
          </Button>
          <Button onClick={() => navigate('/upload')} variant="secondary" className="flex items-center gap-2">
            <Upload className="w-4 h-4" />
            Upload
          </Button>
        </div>
      </motion.div>

      {/* Activity timeline */}
      <div>
        <div className="flex items-center justify-between mb-4">
          <h2 className="text-sm font-medium text-slate-300">Recent Activity</h2>
          <button
            onClick={() => navigate('/regulations')}
            className="text-xs text-slate-500 hover:text-slate-300 transition-colors flex items-center gap-1"
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
            <div className="divide-y divide-slate-800">
              {docs.documents.slice(0, 6).map((doc, idx) => (
                <motion.button
                  key={doc.document_id}
                  initial={{ opacity: 0, x: -8 }}
                  animate={{ opacity: 1, x: 0 }}
                  transition={{ delay: idx * 0.04 }}
                  onClick={() => navigate('/regulations')}
                  className="w-full flex items-center gap-4 p-4 hover:bg-slate-800/40 transition-colors text-left group"
                >
                  <div className="w-9 h-9 rounded-lg bg-blue-500/10 border border-blue-500/20 flex items-center justify-center flex-shrink-0">
                    <FileText className="w-4 h-4 text-blue-400" />
                  </div>
                  <div className="flex-1 min-w-0">
                    <p className="text-sm font-medium truncate">{doc.filename}</p>
                    <p className="text-xs text-slate-500 mt-0.5">{doc.chunk_count} chunks indexed</p>
                  </div>
                  <span className="text-xs text-slate-500 whitespace-nowrap">
                    {doc.indexed_at ? formatDistanceToNow(new Date(doc.indexed_at), { addSuffix: true }) : ''}
                  </span>
                  <ArrowUpRight className="w-3.5 h-3.5 text-slate-600 group-hover:text-slate-400 transition-colors flex-shrink-0" />
                </motion.button>
              ))}
            </div>
          </Card>
        ) : (
          <Card>
            <p className="text-sm text-slate-400 py-6 text-center">No regulations uploaded yet.</p>
          </Card>
        )}
      </div>
    </div>
  )
}
