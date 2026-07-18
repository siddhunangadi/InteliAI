import { useState } from 'react'
import { Check } from 'lucide-react'
import Step1Upload from './Step1Upload'
import Step3Review from './Step3Review'
import Step4Success from './Step4Success'

type Step = 1 | 2 | 3

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

  const handleStep1Complete = (files: File[]) => {
    setData(prev => ({ ...prev, files }))
    setCurrentStep(2)
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
                currentStep >= step.number ? 'bg-signal text-void' : 'bg-panel text-ink-muted'
              }`}
            >
              {currentStep > step.number ? <Check className="w-4 h-4" /> : step.number}
            </div>
            {idx < STEPS.length - 1 && (
              <div className={`flex-1 h-px mx-2 transition-colors ${currentStep > step.number ? 'bg-signal' : 'bg-seam'}`} />
            )}
          </div>
        ))}
      </div>

      {/* Step content -- no entrance motion, the step indicator above already
          communicates the state change. */}
      <div>
        {currentStep === 1 && <Step1Upload onComplete={handleStep1Complete} />}
        {currentStep === 2 && (
          <Step3Review
            files={data.files}
            metadata={data.metadata}
            onChange={setMetadata}
            onComplete={handleStep2Complete}
          />
        )}
        {currentStep === 3 && <Step4Success />}
      </div>
    </div>
  )
}
