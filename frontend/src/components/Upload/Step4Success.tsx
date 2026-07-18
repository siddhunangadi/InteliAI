import { Loader2 } from 'lucide-react'
import { Card, Button } from '@/components/ui'
import { useNavigate } from 'react-router-dom'
import { useUploadJob } from '@/lib/uploadJob'

export default function Step4Success() {
  const navigate = useNavigate()
  const { job } = useUploadJob()

  return (
    <div className="space-y-6 text-center">
      <div>
        <Loader2 className="w-16 h-16 text-blue-400 mx-auto mb-4 animate-spin" />
        <h2 className="text-2xl font-bold">Indexing in Progress</h2>
        <p className="text-slate-400 mt-2">
          {job ? `${job.filenames.length} document${job.filenames.length !== 1 ? 's' : ''} being processed.` : 'Your documents are being processed.'}
        </p>
      </div>

      <Card className="space-y-3">
        <div className="text-left">
          <p className="text-sm font-medium text-slate-400">What's next?</p>
          <ul className="text-sm text-slate-300 mt-2 space-y-1 list-disc list-inside">
            <li>Indexing continues in the background — feel free to navigate away</li>
            <li>You'll get a notification here when it's done</li>
            <li>New documents appear on the Dashboard and Regulations page once indexed</li>
          </ul>
        </div>
      </Card>

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
