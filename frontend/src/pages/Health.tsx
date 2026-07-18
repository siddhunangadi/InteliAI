import { useState, useEffect } from 'react'
import { Zap, Database, RefreshCw, Activity } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { HealthResponse, ReadinessResponse } from '@/lib/types'
import { Card } from '@/components/ui'

export default function Health() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([apiClient.getHealth(), apiClient.getReadiness()])
      .then(([h, r]) => {
        setHealth(h)
        setReadiness(r)
      })
      .finally(() => setLoading(false))
  }, [])

  const checks = [
    {
      name: 'API Service',
      icon: <Zap className="w-6 h-6" />,
      status: health?.status === 'ok' ? 'Operational' : 'Degraded',
      ok: health?.status === 'ok',
    },
    {
      name: 'Vector Search',
      icon: <Database className="w-6 h-6" />,
      status: readiness?.checks?.find(c => c.name === 'pinecone')?.ok ? 'Operational' : 'Degraded',
      ok: readiness?.checks?.find(c => c.name === 'pinecone')?.ok ?? false,
    },
    {
      name: 'Full-Text Search',
      icon: <RefreshCw className="w-6 h-6" />,
      status: readiness?.checks?.find(c => c.name === 'bm25')?.ok ? 'Ready' : 'Degraded',
      ok: readiness?.checks?.find(c => c.name === 'bm25')?.ok ?? false,
    },
    {
      name: 'Embedding Service',
      icon: <Activity className="w-6 h-6" />,
      status: readiness?.checks?.find(c => c.name === 'embedding_provider')?.ok ? 'Ready' : 'Degraded',
      ok: readiness?.checks?.find(c => c.name === 'embedding_provider')?.ok ?? false,
    },
  ]

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-display text-ink">System Health</h1>
        <p className="text-ink-muted mt-1">Real-time monitoring of critical services</p>
      </div>

      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-28 bg-paper-raised rounded-md" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {checks.map((check) => (
            <Card key={check.name}>
              <div className="flex items-start gap-3">
                <div className={check.ok ? 'text-status-verified' : 'text-status-caution'}>{check.icon}</div>
                <div>
                  <p className="font-medium text-ink">{check.name}</p>
                  <p className={`text-label ${check.ok ? 'text-status-verified' : 'text-status-caution'}`}>
                    {check.status}
                  </p>
                </div>
              </div>
            </Card>
          ))}
        </div>
      )}

      {/* Overall Status */}
      <Card>
        <h3 className="text-title text-ink mb-3">Overall System Status</h3>
        <div className="flex items-center gap-3">
          <div className={`w-2 h-2 rounded-full ${health?.status === 'ok' ? 'bg-status-verified' : 'bg-status-caution'}`} />
          <p className={`font-medium ${health?.status === 'ok' ? 'text-status-verified' : 'text-status-caution'}`}>
            {health?.status === 'ok' ? 'All Systems Operational' : 'Some Systems Degraded'}
          </p>
        </div>
      </Card>
    </div>
  )
}
