import { motion } from 'framer-motion'
import { StructuredCitation } from '@/lib/types'
import ConfidenceIndicator from './ConfidenceIndicator'
import CitationPanel from './CitationPanel'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  citations?: StructuredCitation[]
  confidenceScore?: number
  timestamp: Date
}

export default function ChatMessage({
  role,
  content,
  citations,
  confidenceScore,
}: ChatMessageProps) {
  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex ${role === 'user' ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-2xl ${
          role === 'user'
            ? 'bg-blue-600/20 border border-blue-500/30 rounded-lg p-4 text-white'
            : 'space-y-3 w-full'
        }`}
      >
        {role === 'user' ? (
          <p className="text-sm">{content}</p>
        ) : (
          <>
            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 text-slate-100">
              <p className="text-sm leading-relaxed">{content}</p>
            </div>

            {confidenceScore !== undefined && (
              <ConfidenceIndicator score={confidenceScore} />
            )}

            {citations && citations.length > 0 && (
              <CitationPanel citations={citations} />
            )}
          </>
        )}
      </div>
    </motion.div>
  )
}
