import { Loader2, CheckCircle2, XCircle } from 'lucide-react'
import { Card, Button } from '@/components/ui'
import { useNavigate } from 'react-router-dom'
import { useUploadJob } from '@/lib/uploadJob'

// Reflects the real polled job status (queued/processing -> ready/failed via
// GET /jobs/{job_id}, see lib/uploadJob.tsx) instead of a permanent spinner.
export default function Step4Success() {
  const navigate = useNavigate()
  const { job } = useUploadJob()
  const status = job?.status ?? 'processing'
  const count = job?.filenames.length ?? 0
  const label = count ? `${count} document${count !== 1 ? 's' : ''}` : 'Your documents'

  return (
    <div className="space-y-6 text-center">
      <div>
        {status === 'processing' && <Loader2 className="w-16 h-16 text-clay mx-auto mb-4 animate-spin" />}
        {status === 'ready' && <CheckCircle2 className="w-16 h-16 text-status-verified mx-auto mb-4" />}
        {status === 'failed' && <XCircle className="w-16 h-16 text-status-critical mx-auto mb-4" />}
        <h2 className="text-title text-ink">
          {status === 'processing' && 'Indexing in Progress'}
          {status === 'ready' && 'Indexing Complete'}
          {status === 'failed' && 'Indexing Failed'}
        </h2>
        <p className="text-ink-muted mt-2">
          {status === 'processing' && `${label} being processed.`}
          {status === 'ready' && `${label} indexed and searchable.`}
          {status === 'failed' && (job?.status === 'failed' ? 'Indexing failed. Check Audit for details.' : `${label} failed to index.`)}
        </p>
      </div>

      {status === 'processing' && (
        <Card className="space-y-3">
          <div className="text-left">
            <p className="text-label text-ink-muted">What's next?</p>
            <ul className="text-sm text-ink mt-2 space-y-1 list-disc list-inside">
              <li>Indexing continues in the background — feel free to navigate away</li>
              <li>You'll get a notification here when it's done</li>
              <li>New documents appear on the Dashboard and Regulations page once indexed</li>
            </ul>
          </div>
        </Card>
      )}

      <div className="flex gap-3">
        <Button onClick={() => navigate('/')} variant="secondary" className="flex-1">
          Back to Dashboard
        </Button>
        <Button onClick={() => navigate('/chat')} className="flex-1">
          Ask AI
        </Button>
      </div>
    </div>
  )
}
