import { useState } from 'react'
import { Card, Button, Input } from '@/components/ui'

interface Step3ReviewProps {
  metadata: Record<string, unknown>
  onComplete: () => void
}

export default function Step3Review({ metadata: initialMetadata, onComplete }: Step3ReviewProps) {
  const [metadata, setMetadata] = useState(initialMetadata)

  const handleChange = (key: string, value: unknown) => {
    setMetadata(prev => ({ ...prev, [key]: value }))
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Step 3: Review & Edit</h2>
        <p className="text-slate-400 mt-2">Verify extracted information before indexing</p>
      </div>

      <Card>
        <div className="grid grid-cols-2 gap-4">
          <div>
            <label className="text-sm font-medium block mb-2">Authority</label>
            <Input
              value={metadata.authority as string}
              onChange={e => handleChange('authority', e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">Regulation</label>
            <Input
              value={metadata.regulation as string}
              onChange={e => handleChange('regulation', e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">Version</label>
            <Input
              value={metadata.version as string}
              onChange={e => handleChange('version', e.target.value)}
            />
          </div>
          <div>
            <label className="text-sm font-medium block mb-2">Effective Date</label>
            <Input
              type="date"
              value={metadata.effective_date as string}
              onChange={e => handleChange('effective_date', e.target.value)}
            />
          </div>
        </div>
      </Card>

      <Button onClick={onComplete} className="w-full">
        Complete & Index Documents
      </Button>
    </div>
  )
}
