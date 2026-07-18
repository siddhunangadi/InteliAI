import { useState } from 'react'
import { Check, Loader2 } from 'lucide-react'
import { apiClient } from '@/lib/api'
import Step1Upload from './Step1Upload'
import Step3Review from './Step3Review'
import Step4Success from './Step4Success'

type Step = 1 | 2 | 3
type ExtractionStatus = 'success' | 'partial' | null

interface UploadData {
  files: File[]
  metadata: Record<string, unknown>
}

const STEPS = [
  { number: 1, name: 'Upload', description: 'Select documents' },
  { number: 2, name: 'Details', description: 'Optional metadata' },
  { number: 3, name: 'Complete', description: 'Documents indexed' },
]

export default function UploadWorkflow() {
  const [currentStep, setCurrentStep] = useState<Step>(1)
  const [data, setData] = useState<UploadData>({ files: [], metadata: {} })
  const [extracting, setExtracting] = useState(false)
  const [extractionStatus, setExtractionStatus] = useState<ExtractionStatus>(null)

  const handleStep1Complete = async (files: File[]) => {
    setData(prev => ({ ...prev, files }))
    setExtracting(true)
    setExtractionStatus(null)
    try {
      // Only the first file is analyzed -- the metadata form applies to the
      // whole batch (multipart upload has no per-file metadata slot), so
      // extracting from every file would just overwrite the same fields.
      const result = await apiClient.extractMetadata(files[0])
      const suggested = Object.fromEntries(
        Object.entries(result.metadata).filter(([, value]) => value !== null)
      )
      setData(prev => ({ ...prev, metadata: suggested }))
      setExtractionStatus(result.low_confidence ? 'partial' : 'success')
    } catch {
      // Extraction is a convenience, never a blocker -- fall through to a
      // blank form the user fills in manually.
      setExtractionStatus(null)
    } finally {
      setExtracting(false)
      setCurrentStep(2)
    }
  }

  const handleStep2Complete = () => {
    setCurrentStep(3)
  }

  const setMetadata = (metadata: Record<string, unknown>) => {
    setData(prev => ({ ...prev, metadata }))
  }

  return (
    <div className="max-w-4xl space-y-8">
      {/* Progress Steps */}
      <div className="flex justify-between">
        {STEPS.map((step, idx) => (
          <div key={step.number} className="flex items-center flex-1">
            <div
              className={`w-9 h-9 rounded-sm flex items-center justify-center text-sm font-semibold transition-colors ${
                currentStep >= step.number ? 'bg-clay text-paper' : 'bg-paper text-ink-muted'
              }`}
            >
              {currentStep > step.number ? <Check className="w-4 h-4" /> : step.number}
            </div>
            {idx < STEPS.length - 1 && (
              <div className={`flex-1 h-px mx-2 transition-colors ${currentStep > step.number ? 'bg-clay' : 'bg-rule'}`} />
            )}
          </div>
        ))}
      </div>

      {/* Step content -- no entrance motion, the step indicator above already
          communicates the state change. */}
      <div>
        {currentStep === 1 && !extracting && <Step1Upload onComplete={handleStep1Complete} />}
        {extracting && (
          <div className="flex items-center justify-center gap-3 py-24 text-ink-muted">
            <Loader2 className="w-5 h-5 animate-spin" />
            <span>Analyzing document...</span>
          </div>
        )}
        {currentStep === 2 && !extracting && (
          <Step3Review
            files={data.files}
            metadata={data.metadata}
            extractionStatus={extractionStatus}
            onChange={setMetadata}
            onComplete={handleStep2Complete}
          />
        )}
        {currentStep === 3 && <Step4Success />}
      </div>
    </div>
  )
}
