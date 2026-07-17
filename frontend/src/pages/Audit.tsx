import { useState, useEffect } from 'react'
import { isAxiosError } from 'axios'
import { motion } from 'framer-motion'
import { Download } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { AuditEventsResponse } from '@/lib/types'
import { Card, Button } from '@/components/ui'
import AuditTimeline from '@/components/Audit/AuditTimeline'

export default function Audit() {
  const [events, setEvents] = useState<AuditEventsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>()
  const [dateRange, setDateRange] = useState({ start: '', end: '' })

  useEffect(() => {
    apiClient.getAuditEvents(100, 0)
      .then(setEvents)
      .catch(err => {
        console.error('Failed to load audit events:', err)
        if (isAxiosError(err) && err.response?.status === 401) {
          setError('Your API key is missing or invalid. Add it in Settings to view the audit trail.')
        } else {
          setError('Unable to load audit events. Please try again later.')
        }
      })
      .finally(() => setLoading(false))
  }, [])

  const filteredEvents = (events?.events || []).filter(e => {
    const ts = e.timestamp.slice(0, 10)
    if (dateRange.start && ts < dateRange.start) return false
    if (dateRange.end && ts > dateRange.end) return false
    return true
  })

  const handleExportCSV = () => {
    if (!filteredEvents.length) return
    const csv = [
      ['Timestamp', 'Event Type', 'Action', 'Status'],
      ...filteredEvents.map(e => [
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
        <Button onClick={handleExportCSV} disabled={!filteredEvents.length} className="flex items-center gap-2">
          <Download className="w-4 h-4" />
          Export CSV
        </Button>
      </div>

      {error && (
        <Card className="bg-red-500/10 border-red-500/30">
          <p className="text-red-400 text-sm">{error}</p>
        </Card>
      )}

      {/* Timeline */}
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-20 bg-slate-800/50 rounded animate-pulse" />
          ))}
        </div>
      ) : error ? null : (
        <Card>
          <h3 className="text-lg font-semibold mb-6">Activity Timeline</h3>
          <AuditTimeline events={filteredEvents} />
        </Card>
      )}

      {events && !error && (
        <Card>
          <p className="text-sm text-slate-400">
            Showing {filteredEvents.length} of {events.total} events
          </p>
        </Card>
      )}
    </motion.div>
  )
}
