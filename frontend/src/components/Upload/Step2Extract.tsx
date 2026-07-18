import { Card, Button, Input } from '@/components/ui'

const selectClass =
  'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all'

interface Step2ExtractProps {
  files: File[]
  metadata: Record<string, unknown>
  onChange: (metadata: Record<string, unknown>) => void
  onComplete: () => void
}

const DOCUMENT_TYPES = ['general', 'regulation', 'policy', 'contract', 'standard', 'guideline']
const RISK_CATEGORIES = ['low', 'medium', 'high', 'critical']

export default function Step2Extract({ files, metadata, onChange, onComplete }: Step2ExtractProps) {
  const set = (key: string, value: unknown) => onChange({ ...metadata, [key]: value })

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Step 2: Document Details</h2>
        <p className="text-slate-400 mt-2">
          Tag {files.length} document{files.length !== 1 ? 's' : ''} with metadata (optional)
        </p>
      </div>

      <Card>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium block mb-2">Document Type</label>
            <select
              className={selectClass}
              value={(metadata.document_type as string) || 'general'}
              onChange={e => set('document_type', e.target.value)}
            >
              {DOCUMENT_TYPES.map(t => <option key={t} value={t}>{t}</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">Risk Category</label>
            <select
              className={selectClass}
              value={(metadata.risk_category as string) || ''}
              onChange={e => set('risk_category', e.target.value || undefined)}
            >
              <option value="">Unspecified</option>
              {RISK_CATEGORIES.map(r => <option key={r} value={r}>{r}</option>)}
            </select>
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">Authority</label>
            <Input value={(metadata.authority as string) || ''} onChange={e => set('authority', e.target.value)} />
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">Regulation</label>
            <Input value={(metadata.regulation as string) || ''} onChange={e => set('regulation', e.target.value)} />
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">Jurisdiction</label>
            <Input value={(metadata.jurisdiction as string) || ''} onChange={e => set('jurisdiction', e.target.value)} />
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">Effective Date</label>
            <Input
              type="date"
              value={(metadata.effective_date as string) || ''}
              onChange={e => set('effective_date', e.target.value)}
            />
          </div>
        </div>
      </Card>

      <Button onClick={onComplete} className="w-full">Continue to Review</Button>
    </div>
  )
}
