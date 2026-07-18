import { useState } from 'react'
import { FileText, ChevronDown } from 'lucide-react'
import { Card } from '@/components/ui'
import { StructuredCitation } from '@/lib/types'

interface CitationPanelProps {
  citations: StructuredCitation[]
}

export default function CitationPanel({ citations }: CitationPanelProps) {
  const [openId, setOpenId] = useState<string | null>(null)

  if (!citations || citations.length === 0) {
    return null
  }

  return (
    <Card>
      <p className="text-sm font-medium mb-3">Source Documents</p>
      <div className="space-y-2">
        {citations.map((citation) => {
          const isOpen = openId === citation.citation_id
          return (
            <div key={citation.citation_id} className="bg-slate-800/50 rounded text-xs overflow-hidden">
              <button
                type="button"
                onClick={() => setOpenId(isOpen ? null : citation.citation_id)}
                className="w-full flex gap-2 p-2 text-left hover:bg-slate-800 transition-colors"
              >
                <FileText className="w-3 h-3 text-blue-400 flex-shrink-0 mt-0.5" />
                <div className="flex-1 min-w-0">
                  <p className="text-slate-300 line-clamp-1">{citation.document_title}</p>
                  <p className="text-slate-500 text-xs mt-0.5">{citation.display}</p>
                </div>
                <ChevronDown
                  className={`w-3 h-3 text-slate-500 flex-shrink-0 mt-0.5 transition-transform ${isOpen ? 'rotate-180' : ''}`}
                />
              </button>
              {isOpen && (
                <div className="px-2 pb-2">
                  <p className="text-slate-300 leading-relaxed bg-slate-900/60 border border-slate-700/50 rounded p-2 whitespace-pre-wrap">
                    {citation.chunk_text || 'Chunk text unavailable.'}
                  </p>
                </div>
              )}
            </div>
          )
        })}
      </div>
    </Card>
  )
}
