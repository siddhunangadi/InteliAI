import { useEffect, useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { motion } from 'framer-motion'
import { formatDistanceToNow } from 'date-fns'
import { Search, Upload, MessageCircle, FileText } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { DocumentsResponse, DiagnosticsResponse } from '@/lib/types'
import { MetricCard, Card, CardSkeleton, Button } from '@/components/ui'

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

  const chunksCount = docs?.total_chunks ?? 0
  const readiness = diagnostics?.readiness ?? []
  const allReady = readiness.length > 0 && readiness.every(c => c.ok)
  const someDown = readiness.some(c => !c.ok)

  return (
    <div className="space-y-8">
      {/* Hero Section */}
      <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
        <div>
          <h1 className="text-3xl font-bold">Welcome back</h1>
          <p className="text-slate-400 mt-1">
            {docs?.total_documents
              ? `${docs.total_documents} regulation${docs.total_documents !== 1 ? 's' : ''} indexed and searchable.`
              : 'Upload your first regulation to get started.'}
          </p>
        </div>

        {/* Hero Search & Actions */}
        <div className="flex flex-col sm:flex-row gap-3">
          <div className="flex-1 relative">
            <Search className="absolute left-3 top-3 w-5 h-5 text-slate-400" />
            <input
              type="text"
              placeholder="Search regulations, circulars, or acts..."
              className="w-full pl-10 pr-4 py-2.5 bg-slate-900 border border-slate-800 rounded-lg text-slate-300 placeholder-slate-500 focus:outline-none focus:border-slate-700"
              onClick={() => navigate('/regulations')}
              readOnly
            />
          </div>
          <Button onClick={() => navigate('/chat')} className="flex items-center gap-2 bg-blue-600 hover:bg-blue-700">
            <MessageCircle className="w-4 h-4" />
            Ask AI
          </Button>
          <Button onClick={() => navigate('/upload')} variant="secondary" className="flex items-center gap-2">
            <Upload className="w-4 h-4" />
            Upload
          </Button>
        </div>
      </motion.div>

      {/* KPI Metrics */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <CardSkeleton key={i} />
          ))}
        </div>
      ) : (
        <motion.div
          className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4"
          initial={{ opacity: 0 }}
          animate={{ opacity: 1 }}
          transition={{ staggerChildren: 0.05 }}
        >
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
            <MetricCard
              label="Current Regulations"
              value={docs?.total_documents ?? 0}
              unit="active"
            />
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
            <MetricCard
              label="Chunks Indexed"
              value={chunksCount}
              unit="chunks"
            />
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
            <MetricCard
              label="API Requests"
              value={diagnostics?.metrics.request_count ?? 0}
              unit="total"
            />
          </motion.div>
          <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
            <Card>
              <p className="text-slate-400 text-sm font-medium">Compliance Health</p>
              <div className="mt-2">
                <p className={`text-2xl font-bold ${allReady ? 'text-emerald-400' : someDown ? 'text-red-400' : 'text-slate-400'}`}>
                  {readiness.length === 0 ? 'Unknown' : allReady ? 'Healthy' : 'Degraded'}
                </p>
                <p className="text-xs text-slate-400 mt-1">
                  {readiness.length === 0
                    ? 'No diagnostics available'
                    : allReady
                    ? 'All systems operational'
                    : readiness.filter(c => !c.ok).map(c => c.name).join(', ') + ' unavailable'}
                </p>
              </div>
            </Card>
          </motion.div>
        </motion.div>
      )}

      {/* Activity Section */}
      <div className="grid grid-cols-1 lg:grid-cols-2 gap-6">
        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }}>
          <h2 className="text-lg font-semibold mb-4">Recent Uploads</h2>
          <Card>
            {docs?.documents?.length ? (
              <div className="space-y-3">
                {docs.documents.slice(0, 5).map((doc, idx) => (
                  <motion.div
                    key={doc.document_id}
                    initial={{ opacity: 0, x: -20 }}
                    animate={{ opacity: 1, x: 0 }}
                    transition={{ delay: 0.1 * idx }}
                    className="flex items-start justify-between p-3 hover:bg-slate-800/50 rounded-lg transition-colors cursor-pointer"
                    onClick={() => navigate(`/regulations`)}
                  >
                    <div className="flex items-start gap-3 flex-1">
                      <FileText className="w-4 h-4 text-blue-400 mt-1 flex-shrink-0" />
                      <div>
                        <p className="font-medium text-sm">{doc.filename}</p>
                        <p className="text-xs text-slate-400 mt-1">{doc.chunk_count} chunks</p>
                      </div>
                    </div>
                    <span className="text-xs text-slate-400 whitespace-nowrap">
                      {doc.indexed_at
                        ? formatDistanceToNow(new Date(doc.indexed_at), { addSuffix: true })
                        : ''}
                    </span>
                  </motion.div>
                ))}
              </div>
            ) : (
              <p className="text-sm text-slate-400 py-6 text-center">No regulations uploaded yet.</p>
            )}
          </Card>
        </motion.div>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.35 }}>
          <h2 className="text-lg font-semibold mb-4">Most Accessed Regulations</h2>
          <Card>
            <p className="text-sm text-slate-400 py-6 text-center">
              Access tracking isn't available yet.
            </p>
          </Card>
        </motion.div>
      </div>

      {/* Quick Actions */}
      <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.4 }} className="flex flex-wrap gap-3">
        <Button onClick={() => navigate('/chat')} className="flex items-center gap-2">
          <MessageCircle className="w-4 h-4" />
          Ask AI
        </Button>
        <Button onClick={() => navigate('/upload')} variant="secondary" className="flex items-center gap-2">
          <Upload className="w-4 h-4" />
          Upload Regulation
        </Button>
        <Button onClick={() => navigate('/regulations')} variant="secondary" className="flex items-center gap-2">
          Browse Regulations
        </Button>
      </motion.div>
    </div>
  )
}
