import { useEffect, useState } from 'react'
import { Loader } from 'lucide-react'
import { Card, Button } from '@/components/ui'

interface Step2ExtractProps {
  files: File[]
  onComplete: (metadata: Record<string, unknown>) => void
}

export default function Step2Extract({ files, onComplete }: Step2ExtractProps) {
  const [progress, setProgress] = useState(0)
  const [extractedMetadata, setExtractedMetadata] = useState<Record<string, unknown>>({})

  useEffect(() => {
    const interval = setInterval(() => {
      setProgress(prev => {
        if (prev >= 100) {
          clearInterval(interval)
          return 100
        }
        return prev + Math.random() * 30
      })
    }, 500)

    return () => clearInterval(interval)
  }, [])

  useEffect(() => {
    if (progress >= 100) {
      setExtractedMetadata({
        authority: 'RBI',
        regulation: 'Master Circular 2025',
        version: '1.0',
        effective_date: new Date().toISOString().split('T')[0],
        country: 'IN',
        risk_category: 'COMPLIANCE',
      })
    }
  }, [progress])

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Step 2: AI Processing</h2>
        <p className="text-slate-400 mt-2">Extracting document metadata and key information</p>
      </div>

      <Card>
        <div className="flex items-center gap-4">
          <Loader className="w-6 h-6 text-blue-400 animate-spin" />
          <div className="flex-1">
            <p className="font-medium">Processing {files.length} document{files.length !== 1 ? 's' : ''}</p>
            <div className="w-full bg-slate-800 rounded h-2 mt-2 overflow-hidden">
              <div
                className="bg-blue-500 h-full transition-all"
                style={{ width: `${Math.min(progress, 100)}%` }}
              />
            </div>
          </div>
        </div>
      </Card>

      {progress >= 100 && (
        <Button onClick={() => onComplete(extractedMetadata)} className="w-full">
          Review Extracted Information
        </Button>
      )}
    </div>
  )
}
