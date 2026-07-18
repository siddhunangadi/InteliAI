import { useState } from 'react'
import { FileText, ChevronDown } from 'lucide-react'
import { Card } from '@/components/ui'
import { StructuredCitation } from '@/lib/types'

interface CitationPanelProps {
  citations: StructuredCitation[]
}

// DESIGN.md "Citation Preview" -- the signature/trust component. Expands
// inline from the chip (not a modal) with a single height transition,
// metadata as Label-weight text along the top edge, chunk text in a
// Signal-Cyan wash.
// ponytail: the backend doesn't return matched-span offsets for the citation
// (StructuredCitation has no span/highlight field), so the whole chunk body
// gets the clay wash rather than just the matched substring. Add span
// highlighting when the API returns match offsets.
export default function CitationPanel({ citations }: CitationPanelProps) {
  const [openId, setOpenId] = useState<string | null>(null)

  if (!citations || citations.length === 0) {
    return null
  }

  return (
    <Card>
      <p className="text-label text-ink-muted mb-3">Source Documents</p>
      <div className="space-y-2">
        {citations.map((citation) => {
          const isOpen = openId === citation.citation_id
          const meta = [citation.regulation, citation.jurisdiction, citation.section, citation.clause, citation.page ? `p. ${citation.page}` : null]
            .filter(Boolean)
            .join(' · ')
          return (
            <div key={citation.citation_id} className="bg-paper-raised border border-rule rounded-sm text-xs overflow-hidden">
              <button
                type="button"
                onClick={() => setOpenId(isOpen ? null : citation.citation_id)}
                className="w-full flex gap-2 p-2.5 text-left hover:bg-paper transition-colors"
              >
                <FileText className="w-3.5 h-3.5 text-clay flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-ink line-clamp-1">{citation.document_title}</p>
                  {meta && <p className="text-label text-ink-muted mt-0.5">{meta}</p>}
                </div>
                <ChevronDown
                  className={`w-3.5 h-3.5 text-ink-muted flex-shrink-0 mt-0.5 transition-transform duration-150 ${isOpen ? 'rotate-180' : ''}`}
                />
              </button>
              <div
                className="overflow-hidden transition-[max-height] duration-[120ms] ease-out"
                style={{ maxHeight: isOpen ? '20rem' : 0 }}
              >
                <div className="px-2.5 pb-2.5">
                  {/* Verbatim-Gets-Mono Rule: retrieved chunk text is IBM Plex Mono. */}
                  <p className="text-mono-data text-ink bg-clay/[0.15] border border-clay/20 rounded-sm p-2.5 whitespace-pre-wrap">
                    {citation.chunk_text || 'Chunk text unavailable.'}
                  </p>
                </div>
              </div>
            </div>
          )
        })}
      </div>
    </Card>
  )
}
