import { createContext, useContext, useState, useCallback, ReactNode } from 'react'
import { apiClient } from './api'
import { useToast } from '@/components/ui'

interface UploadJobState {
  jobId: string
  filenames: string[]
  status: 'processing' | 'ready' | 'failed'
}

interface UploadJobContextType {
  job: UploadJobState | null
  startUpload: (files: File[], metadata: Record<string, unknown>) => Promise<void>
}

const UploadJobContext = createContext<UploadJobContextType | undefined>(undefined)

// Lives at the app root (see main.tsx), not inside the Upload page component
// -- an in-flight job keeps polling to completion regardless of which route
// is mounted, instead of being abandoned the moment the user navigates away.
export function UploadJobProvider({ children }: { children: ReactNode }) {
  const [job, setJob] = useState<UploadJobState | null>(null)
  const { addToast } = useToast()

  const pollJob = useCallback(async (jobId: string, filenames: string[]) => {
    for (;;) {
      const result = await apiClient.getJobStatus(jobId)
      if (result.status === 'processing') {
        await new Promise(r => setTimeout(r, 1500))
        continue
      }
      setJob({ jobId, filenames, status: result.status })
      if (result.status === 'ready') {
        const failed = result.result?.results.filter(r => r.status !== 'ready') ?? []
        if (failed.length === 0) {
          addToast('success', `${filenames.length} document${filenames.length !== 1 ? 's' : ''} indexed successfully.`)
        } else {
          addToast('warning', `${failed.length} of ${filenames.length} document(s) failed to index.`)
        }
      } else {
        addToast('error', result.error || 'Upload failed.')
      }
      return
    }
  }, [addToast])

  const startUpload = useCallback(async (files: File[], metadata: Record<string, unknown>) => {
    const filenames = files.map(f => f.name)
    const { job_id } = await apiClient.uploadDocumentsAsync(files, metadata)
    setJob({ jobId: job_id, filenames, status: 'processing' })
    pollJob(job_id, filenames) // not awaited -- keeps running after this resolves
  }, [pollJob])

  return (
    <UploadJobContext.Provider value={{ job, startUpload }}>
      {children}
    </UploadJobContext.Provider>
  )
}

export function useUploadJob() {
  const ctx = useContext(UploadJobContext)
  if (!ctx) throw new Error('useUploadJob must be used within UploadJobProvider')
  return ctx
}
