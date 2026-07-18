import { CheckCircle, XCircle } from 'lucide-react'
import { Card, Button } from '@/components/ui'
import { useNavigate } from 'react-router-dom'

interface Step4SuccessProps {
  results: { filename: string; status: string; error: string | null }[]
}

export default function Step4Success({ results }: Step4SuccessProps) {
  const navigate = useNavigate()
  const failed = results.filter(r => r.status !== 'ready')
  const allOk = failed.length === 0

  return (
    <div className="space-y-6 text-center">
      <div>
        {allOk ? (
          <CheckCircle className="w-16 h-16 text-emerald-400 mx-auto mb-4" />
        ) : (
          <XCircle className="w-16 h-16 text-orange-400 mx-auto mb-4" />
        )}
        <h2 className="text-2xl font-bold">
          {allOk ? 'Documents Indexed Successfully' : `${failed.length} of ${results.length} Failed`}
        </h2>
        <p className="text-slate-400 mt-2">
          {allOk
            ? 'Your documents are now available for search and compliance analysis'
            : 'Some documents could not be indexed'}
        </p>
      </div>

      <Card className="text-left space-y-2">
        {results.map(r => (
          <div key={r.filename} className="flex justify-between text-sm p-2 bg-slate-800/50 rounded">
            <span>{r.filename}</span>
            <span className={r.status === 'ready' ? 'text-emerald-400' : 'text-red-400'}>
              {r.status === 'ready' ? 'Indexed' : r.error || 'Failed'}
            </span>
          </div>
        ))}
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
