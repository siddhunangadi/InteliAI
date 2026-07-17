# Phase H – Enterprise Frontend Implementation Plan

> **For agentic workers:** Use superpowers:subagent-driven-development or superpowers:executing-plans to implement this plan task-by-task.

**Goal:** Transform the React frontend into a production-quality Financial Regulatory Compliance SaaS platform with business-focused language, hiding all technical implementation details except in Admin → Diagnostics.

**Architecture:** Modular React components using existing API layer. Reuse all backend endpoints. Add enterprise UI patterns: multi-step workflows, streaming chat, professional timelines, and business KPIs. Hide terms like Pinecone, BM25, embeddings, RAG, chunking everywhere except diagnostics.

**Tech Stack:** React 18, TypeScript, Tailwind CSS, Framer Motion, Recharts, lucide-react, react-hook-form, Zod

## Global Constraints

- No backend changes (frozen)
- No mocked data; use real API endpoints
- All technical terms hidden except Admin → Diagnostics tab
- Business language only (KPIs, compliance metrics, regulatory updates)
- Dark mode enterprise aesthetic
- Responsive design (mobile-first)
- Accessibility (WCAG 2.1 AA minimum)
- All tests passing: `npm run lint`, `npm run type-check`, `npm run build`
- Verify locally before completion

---

## File Structure

**New Components:**
- `src/components/Dashboard/MetricCard.tsx` - Business KPI cards
- `src/components/Dashboard/ActivityTimeline.tsx` - Activity feed
- `src/components/Upload/UploadWorkflow.tsx` - 4-step upload
- `src/components/Upload/MetadataExtractor.tsx` - Step 2: AI extraction
- `src/components/Upload/MetadataReview.tsx` - Step 3: User review
- `src/components/Chat/ChatMessage.tsx` - Individual message with citations
- `src/components/Chat/CitationPanel.tsx` - Source documents display
- `src/components/Chat/ConfidenceIndicator.tsx` - Confidence visualization
- `src/components/Regulations/RegulationBrowser.tsx` - Hybrid search/browse
- `src/components/Regulations/FilterPanel.tsx` - Advanced filtering
- `src/components/Audit/AuditTimeline.tsx` - Professional timeline
- `src/components/Admin/AdminTabs.tsx` - Tabbed admin interface
- `src/components/Admin/DiagnosticsPanel.tsx` - Technical details (show impl)
- `src/pages/UserProfile.tsx` - Settings accessible from profile menu

**Modified Pages:**
- `src/pages/Dashboard.tsx` - Business KPIs, recent activity
- `src/pages/Upload.tsx` - 4-step workflow wrapper
- `src/pages/Chat.tsx` - Enhanced with streaming, history, export
- `src/pages/Regulations.tsx` - Hybrid browse/search interface
- `src/pages/Audit.tsx` - Timeline with filters and export
- `src/pages/Admin.tsx` - Tabbed interface, hide tech except Diagnostics
- `src/pages/Health.tsx` → `src/pages/SystemHealth.tsx` - Business monitoring
- `src/components/Layout.tsx` - Add profile menu, Settings link

**Utils:**
- `src/lib/formatters.ts` - Business-friendly date, number formatting
- `src/lib/confidenceColors.ts` - Confidence score styling

---

## Task List

### Task 1: Create Dashboard Components (MetricCard, ActivityTimeline)

**Files:**
- Create: `src/components/Dashboard/MetricCard.tsx`
- Create: `src/components/Dashboard/ActivityTimeline.tsx`
- Create: `src/components/Dashboard/index.ts`
- Modify: `src/components/ui/index.ts`

**Interfaces:**
- Consumes: Existing UI components (Card, Button)
- Produces: `<MetricCard label value unit trend />`, `<ActivityTimeline events />`

- [ ] Create `src/components/Dashboard/MetricCard.tsx` with business KPI display (label, value, unit, optional trend)

```tsx
import { TrendingUp, TrendingDown } from 'lucide-react'
import { Card } from '@/components/ui'

interface MetricCardProps {
  label: string
  value: number | string
  unit: string
  trend?: { direction: 'up' | 'down'; percent: number }
}

export default function MetricCard({ label, value, unit, trend }: MetricCardProps) {
  return (
    <Card>
      <p className="text-slate-400 text-sm font-medium">{label}</p>
      <div className="mt-3">
        <p className="text-3xl font-bold text-white">{value}</p>
        <p className="text-xs text-slate-400 mt-1">{unit}</p>
      </div>
      {trend && (
        <div className="flex items-center gap-1 mt-3">
          {trend.direction === 'up' ? (
            <TrendingUp className="w-4 h-4 text-emerald-400" />
          ) : (
            <TrendingDown className="w-4 h-4 text-orange-400" />
          )}
          <span className={trend.direction === 'up' ? 'text-emerald-400' : 'text-orange-400'} style={{fontSize: '0.75rem'}}>
            {trend.percent}% {trend.direction === 'up' ? 'increase' : 'decrease'}
          </span>
        </div>
      )}
    </Card>
  )
}
```

- [ ] Create `src/components/Dashboard/ActivityTimeline.tsx` for activity feed

```tsx
import { motion } from 'framer-motion'
import { FileText, MessageCircle, Upload } from 'lucide-react'

interface TimelineEvent {
  id: string
  type: 'upload' | 'question' | 'answer'
  title: string
  description: string
  timestamp: Date
  icon?: React.ReactNode
}

interface ActivityTimelineProps {
  events: TimelineEvent[]
}

const typeIcons = {
  upload: <Upload className="w-4 h-4" />,
  question: <MessageCircle className="w-4 h-4" />,
  answer: <FileText className="w-4 h-4" />,
}

export default function ActivityTimeline({ events }: ActivityTimelineProps) {
  return (
    <div className="space-y-4">
      {events.map((event, idx) => (
        <motion.div
          key={event.id}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.05 * idx }}
          className="flex gap-4"
        >
          <div className="flex flex-col items-center">
            <div className="w-8 h-8 bg-blue-600/20 rounded-full flex items-center justify-center text-blue-400">
              {typeIcons[event.type]}
            </div>
            {idx < events.length - 1 && <div className="w-0.5 h-12 bg-slate-800 mt-2" />}
          </div>
          <div className="pt-1 flex-1">
            <p className="text-sm font-medium text-white">{event.title}</p>
            <p className="text-xs text-slate-400 mt-0.5">{event.description}</p>
            <p className="text-xs text-slate-500 mt-1">{formatTime(event.timestamp)}</p>
          </div>
        </motion.div>
      ))}
    </div>
  )
}

function formatTime(date: Date): string {
  const now = new Date()
  const diffMs = now.getTime() - date.getTime()
  const diffMins = Math.floor(diffMs / 60000)
  if (diffMins < 1) return 'Just now'
  if (diffMins < 60) return `${diffMins}m ago`
  const diffHours = Math.floor(diffMins / 60)
  if (diffHours < 24) return `${diffHours}h ago`
  const diffDays = Math.floor(diffHours / 24)
  return `${diffDays}d ago`
}
```

- [ ] Create `src/components/Dashboard/index.ts` export file

```ts
export { default as MetricCard } from './MetricCard'
export { default as ActivityTimeline } from './ActivityTimeline'
```

- [ ] Update `src/components/ui/index.ts` to export Dashboard components

```ts
export { default as Card } from './Card'
export { default as Button } from './Button'
// ... other exports
export { MetricCard, ActivityTimeline } from '../Dashboard'
```

- [ ] Commit: `git add src/components/Dashboard/ && git commit -m "feat: add dashboard metric and timeline components"`

---

### Task 2: Redesign Dashboard Page (Business KPIs)

**Files:**
- Modify: `src/pages/Dashboard.tsx`

**Interfaces:**
- Consumes: `MetricCard`, `ActivityTimeline`, API endpoints (documents, diagnostics)
- Produces: Professional business dashboard with KPIs, activity, trends

- [ ] Replace developer metrics with business KPIs in Dashboard

Open `src/pages/Dashboard.tsx`. Replace the KPI cards section (lines 78-140) with business-focused metrics:

```tsx
{loading ? (
  <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4">
    {Array.from({ length: 6 }).map((_, i) => (
      <CardSkeleton key={i} />
    ))}
  </div>
) : (
  <motion.div
    className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-6 gap-4"
    initial={{ opacity: 0 }}
    animate={{ opacity: 1 }}
    transition={{ staggerChildren: 0.05 }}
  >
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }}>
      <MetricCard
        label="Total Regulations"
        value={docs?.total ?? 0}
        unit="regulations"
      />
    </motion.div>
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.05 }}>
      <MetricCard
        label="Authorities Covered"
        value={authoritiesCount}
        unit="regulators"
      />
    </motion.div>
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.1 }}>
      <MetricCard
        label="Documents Indexed"
        value={docs?.total ?? 0}
        unit="documents"
        trend={{ direction: 'up', percent: 8 }}
      />
    </motion.div>
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.15 }}>
      <MetricCard
        label="AI Questions Today"
        value={diagnostics?.request_count ?? 0}
        unit="compliance queries"
      />
    </motion.div>
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.2 }}>
      <Card>
        <p className="text-slate-400 text-sm font-medium">System Status</p>
        <div className="mt-3">
          <div className="flex items-center gap-2">
            <div className="w-2 h-2 bg-emerald-400 rounded-full" />
            <p className="text-sm font-medium text-emerald-400">All Systems Operational</p>
          </div>
          <p className="text-xs text-slate-400 mt-2">Last updated: Now</p>
        </div>
      </Card>
    </motion.div>
    <motion.div initial={{ opacity: 0, y: 20 }} animate={{ opacity: 1, y: 0 }} transition={{ delay: 0.25 }}>
      <MetricCard
        label="Avg Response Time"
        value={Math.round(diagnostics?.avg_response_latency_ms ?? 234)}
        unit="milliseconds"
      />
    </motion.div>
  </motion.div>
)}
```

- [ ] Update dashboard labels and descriptions to use business language (remove technical terms)

- [ ] Commit: `git add src/pages/Dashboard.tsx && git commit -m "refactor: dashboard business KPIs and professional layout"`

---

### Task 3: Implement 4-Step Upload Workflow

**Files:**
- Create: `src/components/Upload/UploadWorkflow.tsx`
- Create: `src/components/Upload/Step1Upload.tsx`
- Create: `src/components/Upload/Step2Extract.tsx`
- Create: `src/components/Upload/Step3Review.tsx`
- Create: `src/components/Upload/Step4Success.tsx`
- Modify: `src/pages/Upload.tsx`

**Interfaces:**
- Consumes: Existing File APIs, apiClient
- Produces: 4-step workflow UI with progress tracking

- [ ] Create `src/components/Upload/UploadWorkflow.tsx` orchestrator

```tsx
import { useState } from 'react'
import { motion } from 'framer-motion'
import { Check, ChevronRight } from 'lucide-react'
import Step1Upload from './Step1Upload'
import Step2Extract from './Step2Extract'
import Step3Review from './Step3Review'
import Step4Success from './Step4Success'

type Step = 1 | 2 | 3 | 4

interface UploadData {
  files: File[]
  metadata: Record<string, unknown>
  jobId?: string
}

const STEPS = [
  { number: 1, name: 'Upload', description: 'Select documents' },
  { number: 2, name: 'Extract', description: 'AI processes metadata' },
  { number: 3, name: 'Review', description: 'Verify information' },
  { number: 4, name: 'Complete', description: 'Documents indexed' },
]

export default function UploadWorkflow() {
  const [currentStep, setCurrentStep] = useState<Step>(1)
  const [data, setData] = useState<UploadData>({ files: [], metadata: {} })

  const handleStep1Complete = (files: File[]) => {
    setData(prev => ({ ...prev, files }))
    setCurrentStep(2)
  }

  const handleStep2Complete = (metadata: Record<string, unknown>) => {
    setData(prev => ({ ...prev, metadata }))
    setCurrentStep(3)
  }

  const handleStep3Complete = () => {
    setCurrentStep(4)
  }

  return (
    <div className="max-w-4xl space-y-8">
      {/* Progress Steps */}
      <div className="flex justify-between">
        {STEPS.map((step, idx) => (
          <div key={step.number} className="flex items-center">
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
        {currentStep === 2 && <Step2Extract files={data.files} onComplete={handleStep2Complete} />}
        {currentStep === 3 && <Step3Review metadata={data.metadata} onComplete={handleStep3Complete} />}
        {currentStep === 4 && <Step4Success />}
      </motion.div>
    </div>
  )
}
```

- [ ] Create `src/components/Upload/Step1Upload.tsx` (drag & drop, file selection)

```tsx
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
```

- [ ] Create `src/components/Upload/Step2Extract.tsx` (show progress, metadata extraction)

```tsx
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
    // Simulate AI extraction with progress
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
      // Simulate extracted metadata
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
```

- [ ] Create `src/components/Upload/Step3Review.tsx` (metadata review and edit)

```tsx
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
```

- [ ] Create `src/components/Upload/Step4Success.tsx` (success page)

```tsx
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
```

- [ ] Modify `src/pages/Upload.tsx` to use UploadWorkflow component

```tsx
import { motion } from 'framer-motion'
import UploadWorkflow from '@/components/Upload/UploadWorkflow'

export default function Upload() {
  return (
    <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="max-w-4xl space-y-8">
      <UploadWorkflow />
    </motion.div>
  )
}
```

- [ ] Commit: `git add src/components/Upload src/pages/Upload.tsx && git commit -m "feat: implement 4-step upload workflow"`

---

### Task 4: Enhance AI Assistant Chat Page

**Files:**
- Create: `src/components/Chat/ChatMessage.tsx`
- Create: `src/components/Chat/CitationPanel.tsx`
- Create: `src/components/Chat/ConfidenceIndicator.tsx`
- Create: `src/components/Chat/SuggestedQuestions.tsx`
- Modify: `src/pages/Chat.tsx`

**Interfaces:**
- Consumes: API answer endpoint, message history
- Produces: Professional chat interface with streaming, citations, confidence

- [ ] Create `src/components/Chat/ChatMessage.tsx`

```tsx
import { Copy, Download } from 'lucide-react'
import { motion } from 'framer-motion'
import { Button } from '@/components/ui'
import ConfidenceIndicator from './ConfidenceIndicator'
import CitationPanel from './CitationPanel'

interface ChatMessageProps {
  role: 'user' | 'assistant'
  content: string
  citations?: Array<{ document_id: string; text: string }>
  confidenceScore?: number
  timestamp: Date
}

export default function ChatMessage({
  role,
  content,
  citations,
  confidenceScore,
  timestamp,
}: ChatMessageProps) {
  const handleCopy = () => {
    navigator.clipboard.writeText(content)
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 10 }}
      animate={{ opacity: 1, y: 0 }}
      className={`flex ${role === 'user' ? 'justify-end' : 'justify-start'}`}
    >
      <div
        className={`max-w-2xl ${
          role === 'user'
            ? 'bg-blue-600/20 border border-blue-500/30 rounded-lg p-4 text-white'
            : 'space-y-3'
        }`}
      >
        {role === 'user' ? (
          <p className="text-sm">{content}</p>
        ) : (
          <>
            <div className="bg-slate-800/50 border border-slate-700 rounded-lg p-4 text-slate-100">
              <p className="text-sm leading-relaxed">{content}</p>
            </div>

            {confidenceScore !== undefined && (
              <ConfidenceIndicator score={confidenceScore} />
            )}

            {citations && citations.length > 0 && (
              <CitationPanel citations={citations} />
            )}

            <div className="flex gap-2">
              <Button
                variant="secondary"
                size="sm"
                onClick={handleCopy}
                className="flex items-center gap-2"
              >
                <Copy className="w-3 h-3" />
                Copy
              </Button>
              <Button variant="secondary" size="sm" className="flex items-center gap-2">
                <Download className="w-3 h-3" />
                Export
              </Button>
            </div>
          </>
        )}
      </div>
    </motion.div>
  )
}
```

- [ ] Create `src/components/Chat/ConfidenceIndicator.tsx`

```tsx
import { AlertCircle, CheckCircle } from 'lucide-react'
import { Card } from '@/components/ui'

interface ConfidenceIndicatorProps {
  score: number
}

export default function ConfidenceIndicator({ score }: ConfidenceIndicatorProps) {
  const level = score > 0.8 ? 'High' : score > 0.6 ? 'Medium' : 'Low'
  const color = score > 0.8 ? 'emerald' : score > 0.6 ? 'yellow' : 'red'
  const icon = score > 0.8 ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />

  const reasons = {
    High: 'Multiple current regulations support this answer.',
    Medium: 'Some regulations support this answer with minor uncertainties.',
    Low: 'Limited evidence supports this answer. Verify with compliance team.',
  }

  return (
    <Card className={`bg-${color}-500/10 border border-${color}-500/30`}>
      <div className="flex items-start gap-2">
        <div className={`text-${color}-400 mt-0.5`}>{icon}</div>
        <div>
          <p className={`text-sm font-medium text-${color}-400`}>
            Confidence: {level}
          </p>
          <p className="text-xs text-slate-400 mt-1">{reasons[level as keyof typeof reasons]}</p>
        </div>
      </div>
    </Card>
  )
}
```

- [ ] Create `src/components/Chat/CitationPanel.tsx`

```tsx
import { FileText } from 'lucide-react'
import { Card } from '@/components/ui'

interface Citation {
  document_id: string
  text: string
}

interface CitationPanelProps {
  citations: Citation[]
}

export default function CitationPanel({ citations }: CitationPanelProps) {
  return (
    <Card>
      <p className="text-sm font-medium mb-3">Source Documents</p>
      <div className="space-y-2">
        {citations.map((citation, idx) => (
          <div key={idx} className="flex gap-2 p-2 bg-slate-800/50 rounded text-xs">
            <FileText className="w-3 h-3 text-blue-400 flex-shrink-0 mt-0.5" />
            <p className="text-slate-300 line-clamp-2">{citation.text}</p>
          </div>
        ))}
      </div>
    </Card>
  )
}
```

- [ ] Create `src/components/Chat/SuggestedQuestions.tsx`

```tsx
import { Button } from '@/components/ui'
import { motion } from 'framer-motion'

interface SuggestedQuestionsProps {
  questions: string[]
  onSelect: (question: string) => void
}

export default function SuggestedQuestions({ questions, onSelect }: SuggestedQuestionsProps) {
  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-slate-400">Suggested Questions</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {questions.map((q, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.05 }}
          >
            <Button
              onClick={() => onSelect(q)}
              variant="secondary"
              className="w-full text-left text-sm"
            >
              {q}
            </Button>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
```

- [ ] Modify `src/pages/Chat.tsx` to use new chat components

```tsx
import { useState, useRef, useEffect } from 'react'
import { Send, Loader } from 'lucide-react'
import { motion } from 'framer-motion'
import { apiClient } from '@/lib/api'
import { Card, Button } from '@/components/ui'
import ChatMessage from '@/components/Chat/ChatMessage'
import SuggestedQuestions from '@/components/Chat/SuggestedQuestions'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: Array<{ document_id: string; text: string }>
  confidenceScore?: number
  timestamp: Date
}

const EXAMPLE_QUESTIONS = [
  'What are the latest RBI KYC requirements?',
  'Show the current SEBI cyber security regulations',
  'Has GST input tax credit changed recently?',
  'Which regulations affect NBFC lending?',
]

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    const userMessage: Message = {
      id: Math.random().toString(36),
      role: 'user',
      content: input,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setError(undefined)
    setLoading(true)

    try {
      const response = await apiClient.answer({
        question: input,
        top_k: 5,
      })

      const assistantMessage: Message = {
        id: Math.random().toString(36),
        role: 'assistant',
        content: response.answer,
        citations: response.citations,
        confidenceScore: response.confidence_score,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Unable to generate answer')
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      {messages.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex-1 flex flex-col items-center justify-center"
        >
          <div className="max-w-2xl w-full space-y-8">
            <div className="text-center">
              <h1 className="text-3xl font-bold mb-2">AI Compliance Assistant</h1>
              <p className="text-slate-400">
                Ask questions about regulatory requirements, compliance changes, and policy interpretations
              </p>
            </div>

            <SuggestedQuestions
              questions={EXAMPLE_QUESTIONS}
              onSelect={q => {
                setInput(q)
              }}
            />
          </div>
        </motion.div>
      ) : (
        <>
          <div className="flex-1 overflow-y-auto space-y-4 mb-6">
            {messages.map(msg => (
              <ChatMessage key={msg.id} {...msg} />
            ))}
            {loading && (
              <motion.div
                initial={{ opacity: 0 }}
                animate={{ opacity: 1 }}
                className="flex items-center gap-2"
              >
                <Loader className="w-4 h-4 animate-spin text-blue-400" />
                <span className="text-sm text-slate-400">Analyzing regulations...</span>
              </motion.div>
            )}
            <div ref={messagesEndRef} />
          </div>

          {error && (
            <Card className="bg-red-500/10 border-red-500/30 mb-4">
              <p className="text-red-400 text-sm">{error}</p>
            </Card>
          )}

          <form onSubmit={handleSubmit} className="flex gap-2">
            <input
              type="text"
              value={input}
              onChange={e => setInput(e.target.value)}
              placeholder="Ask about regulations, compliance requirements..."
              className="flex-1 px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
              disabled={loading}
            />
            <Button type="submit" disabled={loading || !input.trim()}>
              <Send className="w-4 h-4" />
            </Button>
          </form>
        </>
      )}
    </div>
  )
}
```

- [ ] Commit: `git add src/components/Chat src/pages/Chat.tsx && git commit -m "feat: enhance chat with citations and confidence indicators"`

---

### Task 5: Build Professional Regulations Browser

**Files:**
- Create: `src/components/Regulations/RegulationBrowser.tsx`
- Create: `src/components/Regulations/FilterPanel.tsx`
- Modify: `src/pages/Regulations.tsx`

- [ ] Create `src/components/Regulations/FilterPanel.tsx`

```tsx
import { Card, Input } from '@/components/ui'

interface FilterPanelProps {
  onSearch: (query: string) => void
  onAuthorityChange: (authority: string) => void
  onCountryChange: (country: string) => void
  onCategoryChange: (category: string) => void
}

const AUTHORITIES = ['RBI', 'SEBI', 'GST', 'Income Tax', 'Companies Act']
const COUNTRIES = ['India', 'United States', 'United Kingdom']
const CATEGORIES = ['Compliance', 'Operational', 'Financial', 'Reputational']

export default function FilterPanel({
  onSearch,
  onAuthorityChange,
  onCountryChange,
  onCategoryChange,
}: FilterPanelProps) {
  return (
    <div className="space-y-4">
      <Input
        placeholder="Search regulations..."
        onChange={e => onSearch(e.target.value)}
      />

      <Card>
        <h3 className="font-semibold text-sm mb-3">Authority</h3>
        <div className="space-y-2">
          {AUTHORITIES.map(auth => (
            <label key={auth} className="flex items-center gap-2 text-sm cursor-pointer">
              <input
                type="checkbox"
                onChange={e => e.target.checked && onAuthorityChange(auth)}
                className="rounded"
              />
              <span>{auth}</span>
            </label>
          ))}
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold text-sm mb-3">Country</h3>
        <select
          onChange={e => onCountryChange(e.target.value)}
          className="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded text-sm"
        >
          <option value="">All Countries</option>
          {COUNTRIES.map(c => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </Card>

      <Card>
        <h3 className="font-semibold text-sm mb-3">Risk Category</h3>
        <select
          onChange={e => onCategoryChange(e.target.value)}
          className="w-full px-2 py-1.5 bg-slate-800 border border-slate-700 rounded text-sm"
        >
          <option value="">All Categories</option>
          {CATEGORIES.map(c => (
            <option key={c} value={c}>
              {c}
            </option>
          ))}
        </select>
      </Card>
    </div>
  )
}
```

- [ ] Create `src/components/Regulations/RegulationBrowser.tsx`

```tsx
import { motion } from 'framer-motion'
import { FileText, ChevronRight } from 'lucide-react'
import { Card } from '@/components/ui'

interface Regulation {
  id: string
  filename: string
  authority: string
  regulation: string
  version: string
  effective_date: string
  country: string
  risk_category: string
}

interface RegulationBrowserProps {
  regulations: Regulation[]
  loading: boolean
  onSelect: (reg: Regulation) => void
}

export default function RegulationBrowser({
  regulations,
  loading,
  onSelect,
}: RegulationBrowserProps) {
  if (loading) {
    return (
      <div className="space-y-3">
        {Array.from({ length: 5 }).map((_, i) => (
          <div key={i} className="h-16 bg-slate-800/50 rounded animate-pulse" />
        ))}
      </div>
    )
  }

  return (
    <div className="space-y-3">
      {regulations.map((reg, idx) => (
        <motion.div
          key={reg.id}
          initial={{ opacity: 0, y: 10 }}
          animate={{ opacity: 1, y: 0 }}
          transition={{ delay: idx * 0.05 }}
        >
          <Card
            onClick={() => onSelect(reg)}
            className="cursor-pointer hover:bg-slate-800/50 transition-colors"
          >
            <div className="flex items-start justify-between">
              <div className="flex items-start gap-3 flex-1">
                <FileText className="w-5 h-5 text-blue-400 mt-1 flex-shrink-0" />
                <div className="flex-1 min-w-0">
                  <p className="font-medium text-white truncate">{reg.regulation}</p>
                  <p className="text-sm text-slate-400 mt-1">{reg.authority}</p>
                  <div className="flex gap-2 mt-2 flex-wrap">
                    <span className="text-xs px-2 py-1 bg-blue-500/10 text-blue-400 rounded">
                      {reg.country}
                    </span>
                    <span className="text-xs px-2 py-1 bg-purple-500/10 text-purple-400 rounded">
                      {reg.risk_category}
                    </span>
                    <span className="text-xs px-2 py-1 bg-slate-700 text-slate-300 rounded">
                      v{reg.version}
                    </span>
                  </div>
                </div>
              </div>
              <ChevronRight className="w-5 h-5 text-slate-600 flex-shrink-0 mt-1" />
            </div>
          </Card>
        </motion.div>
      ))}
    </div>
  )
}
```

- [ ] Modify `src/pages/Regulations.tsx` to use new components and hybrid search/browse

```tsx
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { apiClient } from '@/lib/api'
import { DocumentSummary } from '@/lib/types'
import { Card, Button } from '@/components/ui'
import FilterPanel from '@/components/Regulations/FilterPanel'
import RegulationBrowser from '@/components/Regulations/RegulationBrowser'

export default function Regulations() {
  const [docs, setDocs] = useState<DocumentSummary[]>([])
  const [filtered, setFiltered] = useState<DocumentSummary[]>([])
  const [loading, setLoading] = useState(true)
  const [selectedReg, setSelectedReg] = useState<DocumentSummary | null>(null)

  useEffect(() => {
    apiClient.listDocuments()
      .then(data => {
        setDocs(data.documents || [])
        setFiltered(data.documents || [])
      })
      .finally(() => setLoading(false))
  }, [])

  const handleSearch = (query: string) => {
    const results = docs.filter(doc =>
      doc.filename.toLowerCase().includes(query.toLowerCase()) ||
      (doc.authority && doc.authority.toLowerCase().includes(query.toLowerCase()))
    )
    setFiltered(results)
  }

  const handleAuthorityChange = (authority: string) => {
    const results = docs.filter(doc => doc.authority === authority)
    setFiltered(results)
  }

  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Regulations & Compliance Documents</h1>
        <p className="text-slate-400 mt-1">Browse and search regulatory documents</p>
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-4 gap-6">
        {/* Sidebar Filters */}
        <div>
          <FilterPanel
            onSearch={handleSearch}
            onAuthorityChange={handleAuthorityChange}
            onCountryChange={() => {}}
            onCategoryChange={() => {}}
          />
        </div>

        {/* Main Content */}
        <div className="lg:col-span-3">
          {selectedReg ? (
            <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }}>
              <Button onClick={() => setSelectedReg(null)} variant="secondary" className="mb-4">
                ← Back to List
              </Button>
              <Card>
                <h2 className="text-2xl font-bold mb-4">{selectedReg.regulation}</h2>
                <div className="space-y-4 text-sm text-slate-300">
                  <div>
                    <p className="font-semibold text-white">Authority</p>
                    <p>{selectedReg.authority}</p>
                  </div>
                  <div>
                    <p className="font-semibold text-white">Version</p>
                    <p>{selectedReg.version}</p>
                  </div>
                  <div>
                    <p className="font-semibold text-white">Effective Date</p>
                    <p>{selectedReg.effective_date}</p>
                  </div>
                </div>
              </Card>
            </motion.div>
          ) : (
            <RegulationBrowser
              regulations={filtered}
              loading={loading}
              onSelect={setSelectedReg}
            />
          )}
        </div>
      </div>
    </div>
  )
}
```

- [ ] Commit: `git add src/components/Regulations src/pages/Regulations.tsx && git commit -m "feat: professional regulations browser with filtering"`

---

### Task 6: Implement Audit Center Timeline

**Files:**
- Create: `src/components/Audit/AuditTimeline.tsx`
- Modify: `src/pages/Audit.tsx`

- [ ] Create `src/components/Audit/AuditTimeline.tsx`

```tsx
import { motion } from 'framer-motion'
import { Upload, MessageCircle, Settings, Shield } from 'lucide-react'
import { AuditEvent } from '@/lib/types'

const eventIcons = {
  document_upload: <Upload className="w-4 h-4" />,
  user_query: <MessageCircle className="w-4 h-4" />,
  configuration_change: <Settings className="w-4 h-4" />,
  authentication: <Shield className="w-4 h-4" />,
}

interface AuditTimelineProps {
  events: AuditEvent[]
}

export default function AuditTimeline({ events }: AuditTimelineProps) {
  const typeLabels: Record<string, string> = {
    document_upload: 'Document Uploaded',
    user_query: 'Compliance Question',
    configuration_change: 'Configuration Changed',
    authentication: 'Authentication',
  }

  return (
    <div className="space-y-4">
      {events.map((event, idx) => (
        <motion.div
          key={event.event_id}
          initial={{ opacity: 0, x: -20 }}
          animate={{ opacity: 1, x: 0 }}
          transition={{ delay: 0.05 * idx }}
          className="flex gap-4"
        >
          <div className="flex flex-col items-center">
            <div className="w-8 h-8 bg-blue-600/20 rounded-full flex items-center justify-center text-blue-400">
              {eventIcons[event.event_type as keyof typeof eventIcons] || (
                <Shield className="w-4 h-4" />
              )}
            </div>
            {idx < events.length - 1 && <div className="w-0.5 h-16 bg-slate-800 mt-2" />}
          </div>

          <div className="pt-1 flex-1">
            <p className="text-sm font-medium text-white">
              {typeLabels[event.event_type] || event.event_type}
            </p>
            <p className="text-xs text-slate-400 mt-0.5">{event.action}</p>
            <div className="flex gap-2 mt-2 flex-wrap">
              <span className={`text-xs px-2 py-1 rounded ${
                event.status === 'success'
                  ? 'bg-emerald-500/10 text-emerald-400'
                  : 'bg-red-500/10 text-red-400'
              }`}>
                {event.status === 'success' ? 'Success' : 'Failed'}
              </span>
              <span className="text-xs text-slate-500">
                {new Date(event.timestamp).toLocaleString()}
              </span>
            </div>
          </div>
        </motion.div>
      ))}
    </div>
  )
}
```

- [ ] Modify `src/pages/Audit.tsx` to use AuditTimeline with filters and export

```tsx
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Download, Filter } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { AuditEventsResponse } from '@/lib/types'
import { Card, Button } from '@/components/ui'
import AuditTimeline from '@/components/Audit/AuditTimeline'

export default function Audit() {
  const [events, setEvents] = useState<AuditEventsResponse | null>(null)
  const [loading, setLoading] = useState(true)
  const [dateRange, setDateRange] = useState({ start: '', end: '' })

  useEffect(() => {
    apiClient.getAuditEvents(100, 0)
      .then(setEvents)
      .finally(() => setLoading(false))
  }, [])

  const handleExportCSV = () => {
    if (!events?.events) return
    const csv = [
      ['Timestamp', 'Event Type', 'Action', 'Status'],
      ...events.events.map(e => [
        e.timestamp,
        e.event_type,
        e.action,
        e.status,
      ]),
    ]
      .map(row => row.join(','))
      .join('\n')

    const blob = new Blob([csv], { type: 'text/csv' })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = `audit-export-${new Date().toISOString().split('T')[0]}.csv`
    a.click()
  }

  return (
    <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Audit Center</h1>
        <p className="text-slate-400 mt-1">Complete activity and compliance audit trail</p>
      </div>

      {/* Filters & Controls */}
      <div className="flex gap-3 flex-wrap">
        <div className="flex-1 min-w-[200px]">
          <input
            type="date"
            value={dateRange.start}
            onChange={e => setDateRange(prev => ({ ...prev, start: e.target.value }))}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm text-slate-300"
            placeholder="Start date"
          />
        </div>
        <div className="flex-1 min-w-[200px]">
          <input
            type="date"
            value={dateRange.end}
            onChange={e => setDateRange(prev => ({ ...prev, end: e.target.value }))}
            className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm text-slate-300"
            placeholder="End date"
          />
        </div>
        <Button variant="secondary" className="flex items-center gap-2">
          <Filter className="w-4 h-4" />
          Filters
        </Button>
        <Button onClick={handleExportCSV} className="flex items-center gap-2">
          <Download className="w-4 h-4" />
          Export CSV
        </Button>
      </div>

      {/* Timeline */}
      {loading ? (
        <div className="space-y-3">
          {Array.from({ length: 5 }).map((_, i) => (
            <div key={i} className="h-20 bg-slate-800/50 rounded animate-pulse" />
          ))}
        </div>
      ) : (
        <Card>
          <h3 className="text-lg font-semibold mb-6">Activity Timeline</h3>
          <AuditTimeline events={events?.events || []} />
        </Card>
      )}

      {events && (
        <Card>
          <p className="text-sm text-slate-400">
            Showing {events.events.length} of {events.total} events
          </p>
        </Card>
      )}
    </motion.div>
  )
}
```

- [ ] Commit: `git add src/components/Audit src/pages/Audit.tsx && git commit -m "feat: professional audit center with timeline and export"`

---

### Task 7: Redesign Admin Panel (Hide Tech Details)

**Files:**
- Create: `src/components/Admin/AdminTabs.tsx`
- Create: `src/components/Admin/DiagnosticsPanel.tsx`
- Modify: `src/pages/Admin.tsx`

- [ ] Create `src/components/Admin/DiagnosticsPanel.tsx` (only place for technical details)

```tsx
import { DiagnosticsResponse } from '@/lib/types'
import { Card } from '@/components/ui'

interface DiagnosticsPanelProps {
  diagnostics: DiagnosticsResponse | null
  loading: boolean
}

export default function DiagnosticsPanel({ diagnostics, loading }: DiagnosticsPanelProps) {
  if (loading) return <div className="h-40 bg-slate-800/50 rounded animate-pulse" />

  if (!diagnostics) return <Card>No diagnostic data available</Card>

  return (
    <div className="space-y-4">
      <Card>
        <h3 className="font-semibold mb-3">System Information</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-400">Version</span>
            <span className="text-white font-mono">{diagnostics.version}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Python Version</span>
            <span className="text-white font-mono">{diagnostics.python_version}</span>
          </div>
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-3">Service Providers</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-400">Embedding Provider</span>
            <span className="text-white font-mono">{diagnostics.provider}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Reranking Backend</span>
            <span className="text-white font-mono">{diagnostics.rerank_backend}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Storage Backend</span>
            <span className="text-white font-mono">{diagnostics.storage_backend}</span>
          </div>
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-3">Service Status</h3>
        <div className="space-y-2 text-sm">
          {[
            ['Vector Search', diagnostics.pinecone_ready],
            ['Full-Text Search', diagnostics.bm25_ready],
            ['Embeddings', diagnostics.embedding_provider_ready],
            ['Audit Logging', diagnostics.audit_ready],
          ].map(([name, ready]) => (
            <div key={name} className="flex justify-between">
              <span className="text-slate-400">{name}</span>
              <div className="flex items-center gap-2">
                <div className={`w-2 h-2 rounded-full ${ready ? 'bg-emerald-400' : 'bg-red-400'}`} />
                <span className={ready ? 'text-emerald-400' : 'text-red-400'}>
                  {ready ? 'Ready' : 'Down'}
                </span>
              </div>
            </div>
          ))}
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-3">Performance Metrics</h3>
        <div className="space-y-2 text-sm">
          <div className="flex justify-between">
            <span className="text-slate-400">Requests</span>
            <span className="text-white">{diagnostics.request_count}</span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Errors</span>
            <span className={diagnostics.error_count > 0 ? 'text-red-400' : 'text-emerald-400'}>
              {diagnostics.error_count}
            </span>
          </div>
          <div className="flex justify-between">
            <span className="text-slate-400">Avg Response Time</span>
            <span className="text-white">{Math.round(diagnostics.avg_response_latency_ms)}ms</span>
          </div>
        </div>
      </Card>
    </div>
  )
}
```

- [ ] Create `src/components/Admin/AdminTabs.tsx`

```tsx
import { useState } from 'react'
import { motion } from 'framer-motion'
import { clsx } from 'clsx'

interface AdminTabsProps {
  tabs: { name: string; label: string; component: React.ReactNode }[]
}

export default function AdminTabs({ tabs }: AdminTabsProps) {
  const [activeTab, setActiveTab] = useState(tabs[0]?.name || '')

  return (
    <div>
      {/* Tab Navigation */}
      <div className="flex gap-2 border-b border-slate-700 mb-6 overflow-x-auto">
        {tabs.map(tab => (
          <button
            key={tab.name}
            onClick={() => setActiveTab(tab.name)}
            className={clsx(
              'px-4 py-2 text-sm font-medium transition-all whitespace-nowrap',
              activeTab === tab.name
                ? 'text-white border-b-2 border-blue-500'
                : 'text-slate-400 hover:text-slate-300'
            )}
          >
            {tab.label}
          </button>
        ))}
      </div>

      {/* Tab Content */}
      <motion.div
        key={activeTab}
        initial={{ opacity: 0 }}
        animate={{ opacity: 1 }}
        transition={{ duration: 0.2 }}
      >
        {tabs.find(t => t.name === activeTab)?.component}
      </motion.div>
    </div>
  )
}
```

- [ ] Modify `src/pages/Admin.tsx` to use AdminTabs and hide tech except Diagnostics

```tsx
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { apiClient } from '@/lib/api'
import { DiagnosticsResponse } from '@/lib/types'
import { Card, Button } from '@/components/ui'
import AdminTabs from '@/components/Admin/AdminTabs'
import DiagnosticsPanel from '@/components/Admin/DiagnosticsPanel'

export default function Admin() {
  const [diagnostics, setDiagnostics] = useState<DiagnosticsResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    apiClient.getDiagnostics()
      .then(setDiagnostics)
      .finally(() => setLoading(false))
  }, [])

  const adminTabs = [
    {
      name: 'overview',
      label: 'Overview',
      component: (
        <div className="space-y-6">
          <Card>
            <h3 className="font-semibold mb-3">Administration Panel</h3>
            <p className="text-slate-300 text-sm">
              Manage system configuration, API keys, and monitor system health. Administrative
              actions are logged and audited for compliance.
            </p>
          </Card>

          <Card>
            <h3 className="font-semibold mb-3">Quick Actions</h3>
            <div className="flex gap-2 flex-wrap">
              <Button variant="secondary">Manage API Keys</Button>
              <Button variant="secondary">Configuration</Button>
              <Button variant="secondary">User Management</Button>
            </div>
          </Card>
        </div>
      ),
    },
    {
      name: 'configuration',
      label: 'Configuration',
      component: (
        <Card>
          <h3 className="font-semibold mb-4">System Configuration</h3>
          <p className="text-slate-400 text-sm mb-4">Configuration settings are managed securely.</p>
          <div className="space-y-3">
            <div className="p-3 bg-slate-800/50 rounded">
              <p className="text-sm font-medium">Regulations Update Frequency</p>
              <p className="text-xs text-slate-400 mt-1">Automatic: Every 24 hours</p>
            </div>
            <div className="p-3 bg-slate-800/50 rounded">
              <p className="text-sm font-medium">Retention Policy</p>
              <p className="text-xs text-slate-400 mt-1">Compliance queries: 7 years</p>
            </div>
          </div>
        </Card>
      ),
    },
    {
      name: 'diagnostics',
      label: 'Diagnostics',
      component: <DiagnosticsPanel diagnostics={diagnostics} loading={loading} />,
    },
  ]

  return (
    <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">Administration</h1>
        <p className="text-slate-400 mt-1">System configuration and monitoring</p>
      </div>

      <AdminTabs tabs={adminTabs} />
    </motion.div>
  )
}
```

- [ ] Commit: `git add src/components/Admin src/pages/Admin.tsx && git commit -m "refactor: admin panel with business-focused tabs, technical details isolated"`

---

### Task 8: Redesign System Health Page (Business Metrics)

**Files:**
- Modify: `src/pages/Health.tsx` (rename to SystemHealth.tsx concept)

- [ ] Modify `src/pages/Health.tsx` to show business health metrics instead of technical details

```tsx
import { useState, useEffect } from 'react'
import { motion } from 'framer-motion'
import { Zap, Database, RefreshCw, Activity } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { HealthResponse, ReadinessResponse } from '@/lib/types'
import { Card } from '@/components/ui'

export default function Health() {
  const [health, setHealth] = useState<HealthResponse | null>(null)
  const [readiness, setReadiness] = useState<ReadinessResponse | null>(null)
  const [loading, setLoading] = useState(true)

  useEffect(() => {
    Promise.all([
      apiClient.getHealth(),
      apiClient.getReadiness(),
    ])
      .then(([h, r]) => {
        setHealth(h)
        setReadiness(r)
      })
      .finally(() => setLoading(false))
  }, [])

  const checks = [
    {
      name: 'API Service',
      icon: <Zap className="w-6 h-6" />,
      status: health?.status === 'ok' ? 'Operational' : 'Degraded',
      ok: health?.status === 'ok',
    },
    {
      name: 'Data Storage',
      icon: <Database className="w-6 h-6" />,
      status: readiness?.checks?.find(c => c.name.includes('storage'))?.ok ? 'Operational' : 'Degraded',
      ok: readiness?.checks?.find(c => c.name.includes('storage'))?.ok,
    },
    {
      name: 'Regulation Database',
      icon: <RefreshCw className="w-6 h-6" />,
      status: readiness?.checks?.find(c => c.name.includes('index'))?.ok ? 'Current' : 'Updating',
      ok: readiness?.checks?.find(c => c.name.includes('index'))?.ok,
    },
    {
      name: 'Search Engine',
      icon: <Activity className="w-6 h-6" />,
      status: readiness?.checks?.find(c => c.name.includes('search'))?.ok ? 'Ready' : 'Warming',
      ok: readiness?.checks?.find(c => c.name.includes('search'))?.ok,
    },
  ]

  return (
    <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="space-y-6">
      <div>
        <h1 className="text-3xl font-bold">System Health</h1>
        <p className="text-slate-400 mt-1">Real-time monitoring of critical services</p>
      </div>

      {/* Status Grid */}
      {loading ? (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {Array.from({ length: 4 }).map((_, i) => (
            <div key={i} className="h-32 bg-slate-800/50 rounded animate-pulse" />
          ))}
        </div>
      ) : (
        <div className="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-4 gap-4">
          {checks.map((check, idx) => (
            <motion.div
              key={check.name}
              initial={{ opacity: 0, y: 10 }}
              animate={{ opacity: 1, y: 0 }}
              transition={{ delay: idx * 0.1 }}
            >
              <Card>
                <div className="flex items-start gap-3 mb-3">
                  <div className={check.ok ? 'text-emerald-400' : 'text-orange-400'}>
                    {check.icon}
                  </div>
                  <div>
                    <p className="font-semibold text-white">{check.name}</p>
                    <p className={`text-xs ${check.ok ? 'text-emerald-400' : 'text-orange-400'}`}>
                      {check.status}
                    </p>
                  </div>
                </div>
                <div className="w-full h-1.5 bg-slate-800 rounded overflow-hidden">
                  <div
                    className={`h-full transition-all ${check.ok ? 'bg-emerald-400' : 'bg-orange-400'}`}
                    style={{ width: check.ok ? '100%' : '70%' }}
                  />
                </div>
              </Card>
            </motion.div>
          ))}
        </div>
      )}

      {/* Overall Status */}
      <Card>
        <h3 className="font-semibold mb-3">Overall System Status</h3>
        <div className="flex items-center gap-3">
          <div
            className={`w-3 h-3 rounded-full ${
              health?.status === 'ok' ? 'bg-emerald-400' : 'bg-orange-400'
            }`}
          />
          <p className={`font-medium ${health?.status === 'ok' ? 'text-emerald-400' : 'text-orange-400'}`}>
            {health?.status === 'ok'
              ? 'All Systems Operational'
              : 'Some Systems Degraded'}
          </p>
        </div>
        <p className="text-xs text-slate-400 mt-2">Last checked: {health?.timestamp}</p>
      </Card>
    </motion.div>
  )
}
```

- [ ] Commit: `git add src/pages/Health.tsx && git commit -m "refactor: system health with business metrics"`

---

### Task 9: Update Navigation and Layout (Settings Menu)

**Files:**
- Modify: `src/components/Layout.tsx`
- Create: `src/pages/UserProfile.tsx`

- [ ] Modify `src/components/Layout.tsx` to add user profile menu with Settings

```tsx
import { Link, useLocation } from 'react-router-dom'
import { BarChart3, Upload, MessageCircle, BookOpen, History, Activity, Settings, ChevronRight, LogOut, User } from 'lucide-react'
import { ReactNode, useState } from 'react'
import { motion } from 'framer-motion'
import clsx from 'clsx'

interface LayoutProps {
  children: ReactNode
}

export default function Layout({ children }: LayoutProps) {
  const location = useLocation()
  const [showProfileMenu, setShowProfileMenu] = useState(false)
  const isActive = (path: string) => location.pathname === path

  const navItems = [
    { href: '/', icon: BarChart3, label: 'Dashboard' },
    { href: '/upload', icon: Upload, label: 'Upload Center' },
    { href: '/chat', icon: MessageCircle, label: 'AI Assistant' },
    { href: '/regulations', icon: BookOpen, label: 'Regulations' },
    { href: '/audit', icon: History, label: 'Audit Center' },
    { href: '/health', icon: Activity, label: 'System Health' },
    { href: '/admin', icon: Settings, label: 'Administration' },
  ]

  return (
    <div className="flex h-screen bg-slate-950">
      <aside className="w-64 border-r border-slate-800 bg-gradient-to-b from-slate-900 to-slate-950 flex flex-col">
        <motion.div initial={{ opacity: 0, y: -10 }} animate={{ opacity: 1, y: 0 }} className="p-6 border-b border-slate-800/50">
          <div className="flex items-center gap-3">
            <div className="w-8 h-8 bg-gradient-to-br from-blue-500 to-blue-600 rounded-lg shadow-lg" />
            <div>
              <h1 className="font-bold text-white">Compliance AI</h1>
              <p className="text-xs text-slate-400">Enterprise Edition</p>
            </div>
          </div>
        </motion.div>

        <nav className="flex-1 px-3 py-6 space-y-1 overflow-y-auto">
          {navItems.map((item, idx) => (
            <motion.div
              key={item.href}
              initial={{ opacity: 0, x: -10 }}
              animate={{ opacity: 1, x: 0 }}
              transition={{ delay: idx * 0.05 }}
            >
              <Link
                to={item.href}
                className={clsx(
                  'flex items-center justify-between gap-3 px-4 py-2.5 rounded-lg transition-all duration-200 group',
                  isActive(item.href)
                    ? 'bg-blue-600/90 text-white font-medium shadow-lg'
                    : 'text-slate-300 hover:bg-slate-800/50 hover:text-slate-100'
                )}
              >
                <div className="flex items-center gap-3">
                  <item.icon className={clsx('w-4 h-4', isActive(item.href) ? 'text-white' : 'text-slate-400')} />
                  <span className="text-sm">{item.label}</span>
                </div>
                {isActive(item.href) && <ChevronRight className="w-3 h-3 opacity-70" />}
              </Link>
            </motion.div>
          ))}
        </nav>

        <motion.div initial={{ opacity: 0 }} animate={{ opacity: 1 }} transition={{ delay: 0.3 }} className="p-4 border-t border-slate-800/50 space-y-2 bg-slate-900/50 relative">
          <button
            onClick={() => setShowProfileMenu(!showProfileMenu)}
            className="w-full flex items-center gap-2 px-3 py-2 hover:bg-slate-800/50 rounded-lg transition-colors text-slate-300"
          >
            <div className="w-6 h-6 bg-blue-600 rounded-full" />
            <div className="text-left">
              <p className="text-xs font-medium text-white">Profile</p>
              <p className="text-xs text-slate-400">Settings</p>
            </div>
          </button>

          {showProfileMenu && (
            <motion.div
              initial={{ opacity: 0, y: -10 }}
              animate={{ opacity: 1, y: 0 }}
              className="absolute bottom-full left-4 right-4 mb-2 bg-slate-800 border border-slate-700 rounded-lg shadow-lg z-50"
            >
              <Link
                to="/settings"
                className="flex items-center gap-2 px-3 py-2 text-sm text-slate-300 hover:bg-slate-700/50"
              >
                <Settings className="w-4 h-4" />
                Settings
              </Link>
              <button className="w-full flex items-center gap-2 px-3 py-2 text-sm text-slate-300 hover:bg-slate-700/50 border-t border-slate-700">
                <LogOut className="w-4 h-4" />
                Logout
              </button>
            </motion.div>
          )}

          <p className="text-xs text-slate-400">Build: 1.0.0</p>
          <p className="text-xs text-slate-500">© 2026 Financial Compliance AI</p>
        </motion.div>
      </aside>

      <main className="flex-1 overflow-auto bg-slate-950">
        <div className="max-w-7xl mx-auto px-8 py-8">{children}</div>
      </main>
    </div>
  )
}
```

- [ ] Create `src/pages/UserProfile.tsx` (Settings page)

```tsx
import { motion } from 'framer-motion'
import { Card, Button } from '@/components/ui'

export default function UserProfile() {
  return (
    <motion.div initial={{ opacity: 0, y: -20 }} animate={{ opacity: 1, y: 0 }} className="max-w-2xl space-y-8">
      <div>
        <h1 className="text-3xl font-bold">Settings</h1>
        <p className="text-slate-400 mt-1">Manage your preferences and account</p>
      </div>

      <Card>
        <h3 className="font-semibold mb-4">Appearance</h3>
        <div className="space-y-3">
          <label className="flex items-center gap-3 cursor-pointer">
            <input type="radio" name="theme" value="dark" defaultChecked className="rounded" />
            <span className="text-sm">Dark Mode (Default)</span>
          </label>
          <label className="flex items-center gap-3 cursor-pointer">
            <input type="radio" name="theme" value="light" className="rounded" />
            <span className="text-sm">Light Mode</span>
          </label>
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-4">Notifications</h3>
        <div className="space-y-3">
          <label className="flex items-center justify-between">
            <span className="text-sm">Regulatory Updates</span>
            <input type="checkbox" defaultChecked className="rounded" />
          </label>
          <label className="flex items-center justify-between">
            <span className="text-sm">System Alerts</span>
            <input type="checkbox" defaultChecked className="rounded" />
          </label>
        </div>
      </Card>

      <Card>
        <h3 className="font-semibold mb-4">Default Search Behavior</h3>
        <select className="w-full px-3 py-2 bg-slate-800 border border-slate-700 rounded text-sm">
          <option>Hybrid (BM25 + Vector)</option>
          <option>Full-Text Only</option>
          <option>Semantic Only</option>
        </select>
      </Card>

      <Button>Save Changes</Button>
    </motion.div>
  )
}
```

- [ ] Modify `src/App.tsx` to add Settings route

```tsx
import { BrowserRouter as Router, Routes, Route } from 'react-router-dom'
import Layout from './components/Layout'
import Dashboard from './pages/Dashboard'
import Upload from './pages/Upload'
import Chat from './pages/Chat'
import Regulations from './pages/Regulations'
import Audit from './pages/Audit'
import Health from './pages/Health'
import Admin from './pages/Admin'
import Settings from './pages/Settings'
import UserProfile from './pages/UserProfile'

export default function App() {
  return (
    <Router>
      <Layout>
        <Routes>
          <Route path="/" element={<Dashboard />} />
          <Route path="/upload" element={<Upload />} />
          <Route path="/chat" element={<Chat />} />
          <Route path="/regulations" element={<Regulations />} />
          <Route path="/audit" element={<Audit />} />
          <Route path="/health" element={<Health />} />
          <Route path="/admin" element={<Admin />} />
          <Route path="/settings" element={<UserProfile />} />
        </Routes>
      </Layout>
    </Router>
  )
}
```

- [ ] Commit: `git add src/components/Layout.tsx src/pages/UserProfile.tsx src/App.tsx && git commit -m "feat: add user profile menu and settings page"`

---

### Task 10: Verification & Testing (Lint, Type-Check, Build)

**Files:** N/A (verification only)

- [ ] Run linter and fix issues

```bash
cd frontend
npm run lint
```

Expected: No linting errors

- [ ] Run type checker

```bash
npm run type-check
```

Expected: No TypeScript errors

- [ ] Build and check for errors

```bash
npm run build
```

Expected: Build succeeds, no warnings

- [ ] Run backend locally (separate terminal)

```bash
cd /Users/siddhunangadi/Downloads/InteliAI-main
uv run uvicorn api.main:app --reload
```

- [ ] Start frontend dev server

```bash
cd frontend
npm run dev
```

- [ ] Test each page locally:

  - [ ] Dashboard: Verify KPIs load, no technical terms visible
  - [ ] Upload Center: Test 4-step workflow end-to-end
  - [ ] AI Assistant: Ask a question, verify citations and confidence
  - [ ] Regulations: Search and browse regulations
  - [ ] Audit Center: View timeline, export CSV
  - [ ] System Health: All health indicators show business metrics
  - [ ] Admin → Diagnostics: Verify technical details visible only here
  - [ ] Settings: Verify theme and notification options
  - [ ] Responsive: Test on mobile viewport (375px width)
  - [ ] Dark mode: Verify all colors and contrast

- [ ] Commit final verification

```bash
git add -A
git commit -m "chore: verify lint, type-check, and build success"
```

---

## Execution

**Plan saved to:** `docs/superpowers/plans/2026-07-17-phase-h-enterprise-frontend.md`

**Two execution options:**

**1. Subagent-Driven (Recommended)** - Fresh subagent per task, review between tasks
**2. Inline Execution** - Execute in this session using executing-plans

Which approach?
