import { StructuredCitation } from '@/lib/types'
import ConfidenceIndicator from './ConfidenceIndicator'
import CitationPanel from './CitationPanel'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  citations?: StructuredCitation[]
  confidenceScore?: number
  streaming?: boolean
  timestamp: Date
}

export default function ChatMessage({ role, content, citations, confidenceScore, streaming }: ChatMessageProps) {
  return (
    <div className={`flex ${role === 'user' ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-2xl ${role === 'user' ? 'bg-panel border border-seam rounded-md p-4 text-ink' : 'space-y-3 w-full'}`}>
        {role === 'user' ? (
          <p className="text-sm">{content}</p>
        ) : (
          <>
            <div className="bg-panel border border-seam rounded-md p-4 text-ink">
              <p className="text-sm leading-relaxed max-w-[70ch] whitespace-pre-wrap">
                {content}
                {/* Motion reports real state: token stream in progress, cyan is
                    reserved for AI activity (DESIGN.md One Accent Rule). */}
                {streaming && <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-signal align-middle animate-pulse" />}
              </p>
            </div>

            {confidenceScore !== undefined && <ConfidenceIndicator score={confidenceScore} />}

            {citations && citations.length > 0 && <CitationPanel citations={citations} />}
          </>
        )}
      </div>
    </div>
  )
}
