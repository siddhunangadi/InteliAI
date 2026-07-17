import { motion } from 'framer-motion'
import { FileText, MessageCircle, Upload } from 'lucide-react'

interface TimelineEvent {
  id: string
  type: 'upload' | 'question' | 'answer'
  title: string
  description: string
  timestamp: Date
}

interface ActivityTimelineProps {
  events: TimelineEvent[]
}

const typeIcons = {
  upload: <Upload className="w-4 h-4" />,
  question: <MessageCircle className="w-4 h-4" />,
  answer: <FileText className="w-4 h-4" />,
}

export default function ActivityTimeline({ events }: ActivityTimelineProps) {
  const formatTime = (date: Date): string => {
    const now = new Date()
    const diffMs = now.getTime() - date.getTime()
    const diffMins = Math.floor(diffMs / 60000)
    if (diffMins < 1) return 'Just now'
    if (diffMins < 60) return `${diffMins}m ago`
    const diffHours = Math.floor(diffMins / 60)
    if (diffHours < 24) return `${diffHours}h ago`
    const diffDays = Math.floor(diffHours / 24)
    return `${diffDays}d ago`
  }

  return (
    <div className="space-y-4">
      {events.map((event, idx) => (
        <motion.div
          key={event.id}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.05 * idx }}
          className="flex gap-4"
        >
          <div className="flex flex-col items-center">
            <div className="w-8 h-8 bg-blue-600/20 rounded-full flex items-center justify-center text-blue-400">
              {typeIcons[event.type]}
            </div>
            {idx < events.length - 1 && <div className="w-0.5 h-12 bg-slate-800 mt-2" />}
          </div>
          <div className="pt-1 flex-1">
            <p className="text-sm font-medium text-white">{event.title}</p>
            <p className="text-xs text-slate-400 mt-0.5">{event.description}</p>
            <p className="text-xs text-slate-500 mt-1">{formatTime(event.timestamp)}</p>
          </div>
        </motion.div>
      ))}
    </div>
  )
}
