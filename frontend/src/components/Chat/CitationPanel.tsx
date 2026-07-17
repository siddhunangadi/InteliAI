import { FileText } from 'lucide-react'
import { Card } from '@/components/ui'
import { StructuredCitation } from '@/lib/types'

interface CitationPanelProps {
  citations: StructuredCitation[]
}

export default function CitationPanel({ citations }: CitationPanelProps) {
  if (!citations || citations.length === 0) {
    return null
  }

  return (
    <Card>
      <p className="text-sm font-medium mb-3">Source Documents</p>
      <div className="space-y-2">
        {citations.map((citation) => (
          <div key={citation.citation_id} className="flex gap-2 p-2 bg-slate-800/50 rounded text-xs">
            <FileText className="w-3 h-3 text-blue-400 flex-shrink-0 mt-0.5" />
            <div className="flex-1">
              <p className="text-slate-300 line-clamp-1">{citation.document_title}</p>
              <p className="text-slate-500 text-xs mt-0.5">{citation.display}</p>
            </div>
          </div>
        ))}
      </div>
    </Card>
  )
}
