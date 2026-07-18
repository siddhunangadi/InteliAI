import { createContext, useContext, ReactNode, useState, useCallback } from 'react'
import { motion, AnimatePresence } from 'framer-motion'
import { CheckCircle, AlertCircle, InfoIcon, AlertTriangle, X } from 'lucide-react'

type ToastType = 'success' | 'error' | 'info' | 'warning'

interface Toast {
  id: string
  type: ToastType
  message: string
  duration?: number
}

interface ToastContextType {
  toasts: Toast[]
  addToast: (type: ToastType, message: string, duration?: number) => void
  removeToast: (id: string) => void
}

const ToastContext = createContext<ToastContextType | undefined>(undefined)

export function ToastProvider({ children }: { children: ReactNode }) {
  const [toasts, setToasts] = useState<Toast[]>([])

  const removeToast = useCallback((id: string) => {
    setToasts((prev) => prev.filter((t) => t.id !== id))
  }, [])

  const addToast = useCallback((type: ToastType, message: string, duration = 4000) => {
    const id = Math.random().toString(36)
    setToasts((prev) => [...prev, { id, type, message, duration }])

    if (duration) {
      setTimeout(() => removeToast(id), duration)
    }
  }, [removeToast])

  return (
    <ToastContext.Provider value={{ toasts, addToast, removeToast }}>
      {children}
      <div className="fixed bottom-4 right-4 z-50 space-y-2 pointer-events-none">
        <AnimatePresence>
          {toasts.map((toast) => (
            <ToastItem key={toast.id} toast={toast} onClose={() => removeToast(toast.id)} />
          ))}
        </AnimatePresence>
      </div>
    </ToastContext.Provider>
  )
}

function ToastItem({ toast, onClose }: { toast: Toast; onClose: () => void }) {
  // info uses neutral ink, not clay -- clay is reserved for AI activity and
  // primary actions (DESIGN.md One Accent Rule), not a generic toast accent.
  const icons = {
    success: <CheckCircle className="w-5 h-5 text-status-verified" />,
    error: <AlertCircle className="w-5 h-5 text-status-critical" />,
    info: <InfoIcon className="w-5 h-5 text-ink-muted" />,
    warning: <AlertTriangle className="w-5 h-5 text-status-caution" />,
  }

  const bgColors = {
    success: 'bg-status-verified/10 border-status-verified/30',
    error: 'bg-status-critical/10 border-status-critical/30',
    info: 'bg-paper-raised border-rule',
    warning: 'bg-status-caution/10 border-status-caution/30',
  }

  return (
    <motion.div
      initial={{ opacity: 0, y: 20, x: 20 }}
      animate={{ opacity: 1, y: 0, x: 0 }}
      exit={{ opacity: 0, y: 20, x: 20 }}
      className={`rounded-md border shadow-float p-4 flex items-center gap-3 pointer-events-auto ${bgColors[toast.type]} max-w-md`}
    >
      {icons[toast.type]}
      <span className="flex-1 text-sm text-ink">{toast.message}</span>
      <button onClick={onClose} className="text-ink-muted hover:text-ink">
        <X className="w-4 h-4" />
      </button>
    </motion.div>
  )
}

export function useToast() {
  const context = useContext(ToastContext)
  if (!context) {
    throw new Error('useToast must be used within ToastProvider')
  }
  return context
}
