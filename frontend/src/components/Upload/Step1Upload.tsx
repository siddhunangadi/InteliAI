import { useState } from 'react'
import { Upload as UploadIcon } from 'lucide-react'
import { Card, Button } from '@/components/ui'

interface Step1UploadProps {
  onComplete: (files: File[]) => void
}

export default function Step1Upload({ onComplete }: Step1UploadProps) {
  const [files, setFiles] = useState<File[]>([])
  const [dragActive, setDragActive] = useState(false)

  const handleDrag = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragActive(e.type === 'dragenter' || e.type === 'dragover')
  }

  const handleDrop = (e: React.DragEvent<HTMLDivElement>) => {
    e.preventDefault()
    setDragActive(false)
    if (e.dataTransfer.files) {
      addFiles(Array.from(e.dataTransfer.files))
    }
  }

  const addFiles = (newFiles: File[]) => {
    const validated = newFiles.filter(f => {
      const validTypes = ['pdf', 'docx', 'xlsx', 'csv', 'md', 'txt', 'html']
      return validTypes.some(t => f.name.toLowerCase().endsWith(`.${t}`))
    })
    setFiles(prev => [...prev, ...validated])
  }

  return (
    <div className="space-y-6">
      <div>
        <h2 className="text-2xl font-bold">Step 1: Upload Documents</h2>
        <p className="text-slate-400 mt-2">Select regulatory documents to analyze</p>
      </div>

      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-lg p-12 text-center transition-all ${
          dragActive ? 'border-blue-500 bg-blue-50/5' : 'border-slate-700 hover:border-slate-600'
        }`}
      >
        <UploadIcon className="w-12 h-12 mx-auto mb-4 text-slate-400" />
        <h3 className="text-lg font-semibold mb-2">Drag documents here</h3>
        <p className="text-slate-400 mb-4">or select files (PDF, DOCX, XLSX, CSV, MD, TXT, HTML)</p>
        <label className="inline-block">
          <input
            type="file"
            multiple
            className="hidden"
            onChange={e => e.target.files && addFiles(Array.from(e.target.files))}
            accept=".pdf,.docx,.xlsx,.csv,.md,.txt,.html"
          />
          <Button>Select Files</Button>
        </label>
      </div>

      {files.length > 0 && (
        <Card>
          <h3 className="font-semibold mb-3">Selected Files ({files.length})</h3>
          <div className="space-y-2">
            {files.map((f, i) => (
              <div key={i} className="flex justify-between text-sm p-2 bg-slate-800/50 rounded">
                <span>{f.name}</span>
                <span className="text-slate-400">{(f.size / 1024 / 1024).toFixed(1)} MB</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Button onClick={() => onComplete(files)} disabled={files.length === 0} className="w-full">
        Continue to AI Extraction
      </Button>
    </div>
  )
}
