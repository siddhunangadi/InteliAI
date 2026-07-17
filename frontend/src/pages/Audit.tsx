import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Download, Filter } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { AuditEventsResponse } from '@/lib/types'
import { Card, Button } from '@/components/ui'
import AuditTimeline from '@/components/Audit/AuditTimeline'

export default function Audit() {
  const [events, setEvents] = useState<AuditEventsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [dateRange, setDateRange] = useState({ start: '', end: '' })

  useEffect(() => {
    apiClient.getAuditEvents(100, 0)
      .then(setEvents)
      .finally(() => setLoading(false))
  }, [])

  const handleExportCSV = () => {
    if (!events?.events) return
    const csv = [
      ['Timestamp', 'Event Type', 'Action', 'Status'],
      ...events.events.map(e => [
        e.timestamp,
        e.event_type,
        e.action,
        e.status,
      ]),
    ]
      .map(row => row.join(','))
      .join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `audit-export-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
  }

  return (
    <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Audit Center</h1>
        <p className="text-slate-400 mt-1">Complete activity and compliance audit trail</p>
      </div>

      {/* Filters & Controls */}
      <div className="flex gap-3 flex-wrap">
        <div className="flex-1 min-w-[200px]">
          <input
            type="date"
            value={dateRange.start}
            onChange={e => setDateRange(prev => ({ ...prev, start: e.target.value }))}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm text-slate-300"
            placeholder="Start date"
          />
        </div>
        <div className="flex-1 min-w-[200px]">
          <input
            type="date"
            value={dateRange.end}
            onChange={e => setDateRange(prev => ({ ...prev, end: e.target.value }))}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm text-slate-300"
            placeholder="End date"
          />
        </div>
        <Button variant="secondary" className="flex items-center gap-2">
          <Filter className="w-4 h-4" />
          Filters
        </Button>
        <Button onClick={handleExportCSV} className="flex items-center gap-2">
          <Download className="w-4 h-4" />
          Export CSV
        </Button>
      </div>

      {/* Timeline */}
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-20 bg-slate-800/50 rounded animate-pulse" />
          ))}
        </div>
      ) : (
        <Card>
          <h3 className="text-lg font-semibold mb-6">Activity Timeline</h3>
          <AuditTimeline events={events?.events || []} />
        </Card>
      )}

      {events && (
        <Card>
          <p className="text-sm text-slate-400">
            Showing {events.events.length} of {events.total} events
          </p>
        </Card>
      )}
    </motion.div>
  )
}
