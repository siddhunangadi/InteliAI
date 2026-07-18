import { useRef, useState } from 'react'
import { Upload as UploadIcon } from 'lucide-react'
import { Card, Button } from '@/components/ui'

interface Step1UploadProps {
  onComplete: (files: File[]) => void
}

export default function Step1Upload({ onComplete }: Step1UploadProps) {
  const fileInputRef = useRef<HTMLInputElement>(null)
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
        <h2 className="text-title text-ink">Step 1: Upload Documents</h2>
        <p className="text-ink-muted mt-2">Select regulatory documents to analyze</p>
      </div>

      <div
        onDragEnter={handleDrag}
        onDragLeave={handleDrag}
        onDragOver={handleDrag}
        onDrop={handleDrop}
        className={`border-2 border-dashed rounded-md p-12 text-center transition-colors ${
          dragActive ? 'border-clay bg-clay/[0.06]' : 'border-rule hover:border-ink-muted'
        }`}
      >
        <UploadIcon className="w-12 h-12 mx-auto mb-4 text-ink-muted" />
        <h3 className="text-title text-ink mb-2">Drag documents here</h3>
        <p className="text-ink-muted mb-4">or select files (PDF, DOCX, XLSX, CSV, MD, TXT, HTML)</p>
        <input
          ref={fileInputRef}
          type="file"
          multiple
          className="hidden"
          onChange={e => e.target.files && addFiles(Array.from(e.target.files))}
          accept=".pdf,.docx,.xlsx,.csv,.md,.txt,.html"
        />
        <Button onClick={() => fileInputRef.current?.click()}>Select Files</Button>
      </div>

      {files.length > 0 && (
        <Card>
          <h3 className="text-title text-ink mb-3">Selected Files ({files.length})</h3>
          <div className="space-y-2">
            {files.map((f, i) => (
              <div key={i} className="flex justify-between text-sm p-2 bg-paper-raised rounded-sm">
                <span className="text-ink">{f.name}</span>
                <span className="text-ink-muted">{(f.size / 1024 / 1024).toFixed(1)} MB</span>
              </div>
            ))}
          </div>
        </Card>
      )}

      <Button onClick={() => onComplete(files)} disabled={files.length === 0} className="w-full">
        Continue
      </Button>
    </div>
  )
}
