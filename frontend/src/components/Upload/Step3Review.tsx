import { useState } from 'react'
import { isAxiosError } from 'axios'
import { Card, Button, Input } from '@/components/ui'
import { useUploadJob } from '@/lib/uploadJob'

const selectClass =
  'w-full px-4 py-2 bg-slate-800 border border-slate-700 rounded-lg text-slate-50 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:border-transparent transition-all'

const DOCUMENT_TYPES = ['general', 'regulation', 'policy', 'contract', 'standard', 'guideline']
const RISK_CATEGORIES = ['low', 'medium', 'high', 'critical']

interface Step3ReviewProps {
  files: File[]
  metadata: Record<string, unknown>
  onChange: (metadata: Record<string, unknown>) => void
  onComplete: () => void
}

export default function Step3Review({ files, metadata, onChange, onComplete }: Step3ReviewProps) {
  const { startUpload } = useUploadJob()
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const set = (key: string, value: unknown) => onChange({ ...metadata, [key]: value })

  const submit = async () => {
    setSubmitting(true)
    setError(null)
    try {
      // Hands off to the app-wide upload job (see lib/uploadJob.tsx) --
      // ingestion keeps running and a toast fires on completion even if
      // the user navigates away from this page right after this resolves.
      await startUpload(files, metadata)
      onComplete()
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 401) {
        setError('Your API key is missing or invalid. Add it in Settings to upload documents.')
      } else {
        setError(err instanceof Error ? err.message : 'Upload failed')
      }
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Step 2: Details & Upload</h2>
        <p className="text-slate-400 mt-2">
          Everything below is optional — tag {files.length} document{files.length !== 1 ? 's' : ''} now, or skip straight to upload.
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
              hint="The regulation's legal effective date, not today's date. Leave blank if unsure."
            />
          </div>
        </div>
      </Card>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      <div className="flex gap-3">
        <Button onClick={submit} disabled={submitting} className="flex-1">
          {submitting ? 'Starting upload...' : 'Upload & Index'}
        </Button>
      </div>
    </div>
  )
}
