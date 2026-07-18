import { useMemo, useState } from 'react'
import { StructuredCitation, ConfidenceMetrics, ClaimResult } from '@/lib/types'
import ConfidenceIndicator from './ConfidenceIndicator'
import CitationPanel from './CitationPanel'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  citations?: StructuredCitation[]
  confidence?: ConfidenceMetrics
  claimResults?: ClaimResult[]
  streaming?: boolean
  timestamp: Date
}

export default function ChatMessage({ role, content, citations, confidence, claimResults, streaming }: ChatMessageProps) {
  const [activeId, setActiveId] = useState<string | null>(null)

  const citationIndex = useMemo(() => {
    const map = new Map<string, number>()
    citations?.forEach((c, i) => map.set(c.citation_id, i + 1))
    return map
  }, [citations])

  const jumpToCitation = (citationId: string) => {
    setActiveId((prev) => (prev === citationId ? prev : citationId))
    document.getElementById(`citation-${citationId}`)?.scrollIntoView({ behavior: 'smooth', block: 'nearest' })
  }

  // Inline citation markers (DESIGN.md-aligned: numbers, not decoration) --
  // only once claims have actually been verified against citations. During
  // streaming, or when the answer had no atomic claims to verify (e.g. a
  // one-line "no information" response), fall back to the plain paragraph.
  const hasInlineCitations = !streaming && claimResults && claimResults.length > 0

  return (
    <div className={`flex ${role === 'user' ? 'justify-end' : 'justify-start'}`}>
      <div className={`max-w-2xl ${role === 'user' ? 'bg-paper border border-rule rounded-md p-4 text-ink' : 'space-y-3 w-full'}`}>
        {role === 'user' ? (
          <p className="text-sm">{content}</p>
        ) : (
          <>
            <div className="bg-paper border border-rule rounded-md p-4 text-ink">
              {hasInlineCitations ? (
                <div className="text-sm leading-relaxed max-w-[70ch] space-y-2">
                  {claimResults.map((result, i) => {
                    const ids = result.claim.citation_ids.filter((id) => citationIndex.has(id))
                    return (
                      <p key={i} className="whitespace-pre-wrap">
                        {result.claim.text}
                        {ids.map((id) => (
                          <button
                            key={id}
                            type="button"
                            onClick={() => jumpToCitation(id)}
                            className="text-clay text-[0.7rem] align-super ml-0.5 hover:underline"
                          >
                            [{citationIndex.get(id)}]
                          </button>
                        ))}
                      </p>
                    )
                  })}
                </div>
              ) : (
                <p className="text-sm leading-relaxed max-w-[70ch] whitespace-pre-wrap">
                  {content}
                  {/* Motion reports real state: token stream in progress, cyan is
                      reserved for AI activity (DESIGN.md One Accent Rule). */}
                  {streaming && <span className="inline-block w-1.5 h-3.5 ml-0.5 bg-clay align-middle animate-pulse" />}
                </p>
              )}
            </div>

            {confidence && <ConfidenceIndicator confidence={confidence} />}

            {citations && citations.length > 0 && (
              <CitationPanel citations={citations} activeId={activeId} onToggle={(id) => setActiveId((prev) => (prev === id ? null : id))} />
            )}
          </>
        )}
      </div>
    </div>
  )
}
