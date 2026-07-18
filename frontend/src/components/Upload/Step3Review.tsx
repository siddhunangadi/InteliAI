import { useState } from 'react'
import { isAxiosError } from 'axios'
import { Card, Button, Input } from '@/components/ui'
import { apiClient } from '@/lib/api'

interface Step3ReviewProps {
  files: File[]
  metadata: Record<string, unknown>
  onChange: (metadata: Record<string, unknown>) => void
  onComplete: (results: { filename: string; status: string; error: string | null }[]) => void
}

export default function Step3Review({ files, metadata, onChange, onComplete }: Step3ReviewProps) {
  const [submitting, setSubmitting] = useState(false)
  const [error, setError] = useState<string | null>(null)

  const handleChange = (key: string, value: unknown) => {
    onChange({ ...metadata, [key]: value })
  }

  const submit = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const { job_id } = await apiClient.uploadDocumentsAsync(files, metadata)
      // Poll until the background ingestion worker finishes (see api/jobs.py).
      for (;;) {
        const job = await apiClient.getJobStatus(job_id)
        if (job.status === 'processing') {
          await new Promise(r => setTimeout(r, 1000))
          continue
        }
        if (job.status === 'failed') {
          throw new Error(job.error || 'Ingestion failed')
        }
        onComplete(job.result?.results || [])
        return
      }
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 401) {
        setError('Your API key is missing or invalid. Add it in Settings to upload documents.')
      } else {
        setError(err instanceof Error ? err.message : 'Upload failed')
      }
    } finally {
      setSubmitting(false)
    }
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Step 3: Review & Edit</h2>
        <p className="text-slate-400 mt-2">Verify information before indexing</p>
      </div>

      <Card>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium block mb-2">Authority</label>
            <Input
              value={(metadata.authority as string) || ''}
              onChange={e => handleChange('authority', e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">Regulation</label>
            <Input
              value={(metadata.regulation as string) || ''}
              onChange={e => handleChange('regulation', e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">Jurisdiction</label>
            <Input
              value={(metadata.jurisdiction as string) || ''}
              onChange={e => handleChange('jurisdiction', e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">Effective Date</label>
            <Input
              type="date"
              value={(metadata.effective_date as string) || ''}
              onChange={e => handleChange('effective_date', e.target.value)}
            />
          </div>
        </div>
      </Card>

      {error && (
        <div className="p-4 bg-red-500/10 border border-red-500/30 rounded-lg text-red-400 text-sm">
          {error}
        </div>
      )}

      <Button onClick={submit} disabled={submitting} className="w-full">
        {submitting ? 'Uploading...' : 'Complete & Index Documents'}
      </Button>
    </div>
  )
}
