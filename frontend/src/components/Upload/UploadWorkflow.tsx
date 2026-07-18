import { useState } from 'react'
import { motion } from 'framer-motion'
import { Check } from 'lucide-react'
import Step1Upload from './Step1Upload'
import Step2Extract from './Step2Extract'
import Step3Review from './Step3Review'
import Step4Success from './Step4Success'

type Step = 1 | 2 | 3 | 4
type Result = { filename: string; status: string; error: string | null }

interface UploadData {
  files: File[]
  metadata: Record<string, unknown>
  results: Result[]
}

const STEPS = [
  { number: 1, name: 'Upload', description: 'Select documents' },
  { number: 2, name: 'Details', description: 'Add metadata' },
  { number: 3, name: 'Review', description: 'Verify information' },
  { number: 4, name: 'Complete', description: 'Documents indexed' },
]

export default function UploadWorkflow() {
  const [currentStep, setCurrentStep] = useState<Step>(1)
  const [data, setData] = useState<UploadData>({ files: [], metadata: {}, results: [] })

  const handleStep1Complete = (files: File[]) => {
    setData(prev => ({ ...prev, files }))
    setCurrentStep(2)
  }

  const handleStep2Complete = () => {
    setCurrentStep(3)
  }

  const handleStep3Complete = (results: Result[]) => {
    setData(prev => ({ ...prev, results }))
    setCurrentStep(4)
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
            <motion.div
              className={`w-10 h-10 rounded-full flex items-center justify-center font-bold transition-all ${
                currentStep >= step.number
                  ? 'bg-blue-600 text-white'
                  : 'bg-slate-800 text-slate-400'
              }`}
              initial={{ scale: 0.8 }}
              animate={{ scale: 1 }}
            >
              {currentStep > step.number ? <Check className="w-5 h-5" /> : step.number}
            </motion.div>
            {idx < STEPS.length - 1 && (
              <div
                className={`flex-1 h-1 mx-2 transition-all ${
                  currentStep > step.number ? 'bg-blue-600' : 'bg-slate-800'
                }`}
              />
            )}
          </div>
        ))}
      </div>

      {/* Step Content */}
      <motion.div
        key={currentStep}
        initial={{ opacity: 0, y: 10 }}
        animate={{ opacity: 1, y: 0 }}
        exit={{ opacity: 0, y: -10 }}
      >
        {currentStep === 1 && <Step1Upload onComplete={handleStep1Complete} />}
        {currentStep === 2 && (
          <Step2Extract
            files={data.files}
            metadata={data.metadata}
            onChange={setMetadata}
            onComplete={handleStep2Complete}
          />
        )}
        {currentStep === 3 && (
          <Step3Review
            files={data.files}
            metadata={data.metadata}
            onChange={setMetadata}
            onComplete={handleStep3Complete}
          />
        )}
        {currentStep === 4 && <Step4Success results={data.results} />}
      </motion.div>
    </div>
  )
}
