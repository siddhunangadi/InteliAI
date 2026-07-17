import { CheckCircle } from 'lucide-react'
import { Card, Button } from '@/components/ui'
import { useNavigate } from 'react-router-dom'

export default function Step4Success() {
  const navigate = useNavigate()

  return (
    <div className="space-y-6 text-center">
      <div>
        <CheckCircle className="w-16 h-16 text-emerald-400 mx-auto mb-4" />
        <h2 className="text-2xl font-bold">Documents Indexed Successfully</h2>
        <p className="text-slate-400 mt-2">Your documents are now available for search and compliance analysis</p>
      </div>

      <Card className="space-y-3">
        <div className="text-left">
          <p className="text-sm font-medium text-slate-400">What's next?</p>
          <ul className="text-sm text-slate-300 mt-2 space-y-1 list-disc list-inside">
            <li>Browse regulations in the Regulations section</li>
            <li>Ask compliance questions in AI Assistant</li>
            <li>View indexed documents in the audit trail</li>
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
