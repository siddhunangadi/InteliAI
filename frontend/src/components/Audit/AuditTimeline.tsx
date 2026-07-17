import { motion } from 'framer-motion'
import { Upload, MessageCircle, Settings, Shield } from 'lucide-react'
import { AuditEvent } from '@/lib/types'

const eventIcons = {
  document_upload: <Upload className="w-4 h-4" />,
  user_query: <MessageCircle className="w-4 h-4" />,
  configuration_change: <Settings className="w-4 h-4" />,
  authentication: <Shield className="w-4 h-4" />,
}

interface AuditTimelineProps {
  events: AuditEvent[]
}

export default function AuditTimeline({ events }: AuditTimelineProps) {
  const typeLabels: Record<string, string> = {
    document_upload: 'Document Uploaded',
    user_query: 'Compliance Question',
    configuration_change: 'Configuration Changed',
    authentication: 'Authentication',
  }

  return (
    <div className="space-y-4">
      {events.map((event, idx) => (
        <motion.div
          key={event.event_id}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.05 * idx }}
          className="flex gap-4"
        >
          <div className="flex flex-col items-center">
            <div className="w-8 h-8 bg-blue-600/20 rounded-full flex items-center justify-center text-blue-400">
              {eventIcons[event.event_type as keyof typeof eventIcons] || (
                <Shield className="w-4 h-4" />
              )}
            </div>
            {idx < events.length - 1 && <div className="w-0.5 h-16 bg-slate-800 mt-2" />}
          </div>

          <div className="pt-1 flex-1">
            <p className="text-sm font-medium text-white">
              {typeLabels[event.event_type] || event.event_type}
            </p>
            <p className="text-xs text-slate-400 mt-0.5">{event.action}</p>
            <div className="flex gap-2 mt-2 flex-wrap">
              <span className={`text-xs px-2 py-1 rounded ${
                event.status === 'success'
                  ? 'bg-emerald-500/10 text-emerald-400'
                  : 'bg-red-500/10 text-red-400'
              }`}>
                {event.status === 'success' ? 'Success' : 'Failed'}
              </span>
              <span className="text-xs text-slate-500">
                {new Date(event.timestamp).toLocaleString()}
              </span>
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  )
}
