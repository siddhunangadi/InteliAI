import { useState, useEffect } from 'react'
import { Zap, Database, RefreshCw, Activity } from 'lucide-react'
import { motion } from 'framer-motion'
import { apiClient } from '@/lib/api'
import { HealthResponse, ReadinessResponse } from '@/lib/types'
import { Card } from '@/components/ui'

export default function Health() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      apiClient.getHealth(),
      apiClient.getReadiness(),
    ])
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
    <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">System Health</h1>
        <p className="text-slate-400 mt-1">Real-time monitoring of critical services</p>
      </div>

      {/* Status Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-32 bg-slate-800/50 rounded animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {checks.map((check, idx) => (
            <motion.div
              key={check.name}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
            >
              <Card>
                <div className="flex items-start gap-3 mb-3">
                  <div className={check.ok ? 'text-emerald-400' : 'text-orange-400'}>
                    {check.icon}
                  </div>
                  <div>
                    <p className="font-semibold text-white">{check.name}</p>
                    <p className={`text-xs ${check.ok ? 'text-emerald-400' : 'text-orange-400'}`}>
                      {check.status}
                    </p>
                  </div>
                </div>
                <div className="w-full h-1.5 bg-slate-800 rounded overflow-hidden">
                  <div
                    className={`h-full transition-all ${check.ok ? 'bg-emerald-400' : 'bg-orange-400'}`}
                    style={{ width: check.ok ? '100%' : '70%' }}
                  />
                </div>
              </Card>
            </motion.div>
          ))}
        </div>
      )}

      {/* Overall Status */}
      <Card>
        <h3 className="font-semibold mb-3">Overall System Status</h3>
        <div className="flex items-center gap-3">
          <div
            className={`w-3 h-3 rounded-full ${
              health?.status === 'ok' ? 'bg-emerald-400' : 'bg-orange-400'
            }`}
          />
          <p className={`font-medium ${health?.status === 'ok' ? 'text-emerald-400' : 'text-orange-400'}`}>
            {health?.status === 'ok'
              ? 'All Systems Operational'
              : 'Some Systems Degraded'}
          </p>
        </div>
        {health?.status === 'ok' && (
          <p className="text-xs text-emerald-400 mt-2">✓ All services healthy</p>
        )}
      </Card>
    </motion.div>
  )
}
