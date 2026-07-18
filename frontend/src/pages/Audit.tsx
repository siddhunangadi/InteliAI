import { useState, useEffect } from 'react'
import { isAxiosError } from 'axios'
import { Download } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { AuditEventsResponse } from '@/lib/types'
import { Card, Button } from '@/components/ui'
import AuditTimeline from '@/components/Audit/AuditTimeline'

const EVENT_TYPES = ['query', 'upload', 'deletion', 'supersession', 'auth_failure', 'admin_action']
const STATUSES = ['success', 'failure']

export default function Audit() {
  const [events, setEvents] = useState<AuditEventsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [error, setError] = useState<string>()
  const [dateRange, setDateRange] = useState({ start: '', end: '' })
  const [eventType, setEventType] = useState('')
  const [status, setStatus] = useState('')
  const [role, setRole] = useState('')

  useEffect(() => {
    setLoading(true)
    apiClient.getAuditEvents({
      event_type: eventType || undefined,
      status: status || undefined,
      role: role || undefined,
    })
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
  }, [eventType, status, role])

  // Date range stays a client-side filter -- the server filter is start/end
  // ISO datetimes, but a plain date picker is friendlier here and the event
  // set per page is small enough that filtering the already-fetched page is fine.
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
      ...filteredEvents.map(e => [e.timestamp, e.event_type, e.action, e.status]),
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
    <div className="space-y-6">
      <div>
        <h1 className="text-display text-ink">Audit Center</h1>
        <p className="text-ink-muted mt-1">Complete activity and compliance audit trail</p>
      </div>

      {/* Filters -- event_type/status/role are real server-side query params
          on GET /audit/events (see api/routes.py list_audit_events). */}
      <div className="flex gap-3 flex-wrap">
        <select className="input flex-1 min-w-[160px]" value={eventType} onChange={(e) => setEventType(e.target.value)}>
          <option value="">All event types</option>
          {EVENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
        </select>
        <select className="input flex-1 min-w-[140px]" value={status} onChange={(e) => setStatus(e.target.value)}>
          <option value="">All statuses</option>
          {STATUSES.map(s => <option key={s} value={s}>{s}</option>)}
        </select>
        <input
          type="text"
          placeholder="Filter by role..."
          value={role}
          onChange={(e) => setRole(e.target.value)}
          className="input flex-1 min-w-[140px]"
        />
        <input
          type="date"
          value={dateRange.start}
          onChange={e => setDateRange(prev => ({ ...prev, start: e.target.value }))}
          className="input flex-1 min-w-[150px]"
        />
        <input
          type="date"
          value={dateRange.end}
          onChange={e => setDateRange(prev => ({ ...prev, end: e.target.value }))}
          className="input flex-1 min-w-[150px]"
        />
        <Button onClick={handleExportCSV} disabled={!filteredEvents.length} icon={<Download className="w-4 h-4" />}>
          Export CSV
        </Button>
      </div>

      {error && (
        <Card className="bg-status-critical/10 border-status-critical/30">
          <p className="text-status-critical text-sm">{error}</p>
        </Card>
      )}

      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-20 bg-paper-raised rounded-md" />
          ))}
        </div>
      ) : error ? null : filteredEvents.length === 0 ? (
        <Card>
          <p className="text-ink-muted text-center py-8">No audit events match these filters.</p>
        </Card>
      ) : (
        <Card>
          <h3 className="text-title text-ink mb-6">Activity Timeline</h3>
          <AuditTimeline events={filteredEvents} />
        </Card>
      )}

      {events && !error && (
        <Card>
          <p className="text-sm text-ink-muted">
            Showing {filteredEvents.length} of {events.total} events
          </p>
        </Card>
      )}
    </div>
  )
}
