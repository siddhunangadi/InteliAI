import { Upload, MessageCircle, Trash2, RefreshCw, ShieldAlert, Settings, Shield } from 'lucide-react'
import { AuditEvent } from '@/lib/types'

// Matches the real backend EventType (rag_hybrid_search/audit.py) --
// "query", "upload", "deletion", "supersession", "auth_failure",
// "admin_action". The old map used document_upload/user_query/
// configuration_change/authentication, which never matched a real event,
// so most rows fell through to the generic fallback icon.
const eventIcons: Record<string, JSX.Element> = {
  query: <MessageCircle className="w-4 h-4" />,
  upload: <Upload className="w-4 h-4" />,
  deletion: <Trash2 className="w-4 h-4" />,
  supersession: <RefreshCw className="w-4 h-4" />,
  auth_failure: <ShieldAlert className="w-4 h-4" />,
  admin_action: <Settings className="w-4 h-4" />,
}

const typeLabels: Record<string, string> = {
  query: 'Question Asked',
  upload: 'Document Uploaded',
  deletion: 'Document Deleted',
  supersession: 'Document Superseded',
  auth_failure: 'Authentication Failure',
  admin_action: 'Admin Action',
}

interface AuditTimelineProps {
  events: AuditEvent[]
}

export default function AuditTimeline({ events }: AuditTimelineProps) {
  return (
    <div className="space-y-4">
      {events.map((event, idx) => (
        <div key={event.event_id} className="flex gap-4">
          <div className="flex flex-col items-center">
            <div className="w-8 h-8 bg-paper-raised border border-rule rounded-full flex items-center justify-center text-ink-muted">
              {eventIcons[event.event_type] || <Shield className="w-4 h-4" />}
            </div>
            {idx < events.length - 1 && <div className="w-px h-16 bg-rule mt-2" />}
          </div>

          <div className="pt-1 flex-1">
            <p className="text-sm font-medium text-ink">
              {typeLabels[event.event_type] || event.event_type}
            </p>
            <p className="text-label text-ink-muted mt-0.5">{event.action}</p>
            <div className="flex gap-2 mt-2 flex-wrap items-center">
              <span className={event.status === 'success' ? 'badge badge-verified' : 'badge badge-critical'}>
                {event.status === 'success' ? 'Success' : 'Failed'}
              </span>
              {event.role && <span className="badge bg-paper-raised border border-rule text-ink-muted">{event.role}</span>}
              <span className="text-mono-data text-ink-muted">
                {new Date(event.timestamp).toLocaleString()}
              </span>
            </div>
          </div>
        </div>
      ))}
    </div>
  )
}
