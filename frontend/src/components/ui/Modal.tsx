import { ReactNode } from 'react'
import { X } from 'lucide-react'
import clsx from 'clsx'
import { Button } from './Button'

interface ModalProps {
  isOpen: boolean
  onClose: () => void
  title: string
  children: ReactNode
  footer?: ReactNode
  size?: 'sm' | 'md' | 'lg'
}

const sizeClasses = {
  sm: 'max-w-sm',
  md: 'max-w-md',
  lg: 'max-w-2xl',
}

export function Modal({ isOpen, onClose, title, children, footer, size = 'md' }: ModalProps) {
  if (!isOpen) return null

  return (
    <div className="fixed inset-0 z-50 flex items-center justify-center">
      <div className="absolute inset-0 bg-ink/40" onClick={onClose} />
      {/* Modals are the one portal/floating case DESIGN.md allows shadow-float on. */}
      <div className={clsx('relative bg-paper-raised border border-rule rounded-md shadow-float w-full mx-4', sizeClasses[size])}>
        <div className="flex items-center justify-between p-6 border-b border-rule">
          <h2 className="text-title text-ink">{title}</h2>
          <button onClick={onClose} className="text-ink-muted hover:text-ink transition-colors">
            <X className="w-5 h-5" />
          </button>
        </div>

        <div className="p-6">{children}</div>

        {footer && <div className="flex gap-3 p-6 border-t border-rule justify-end">{footer}</div>}
      </div>
    </div>
  )
}

export function ConfirmDialog({
  isOpen,
  onClose,
  onConfirm,
  title,
  description,
  confirmText = 'Confirm',
  cancelText = 'Cancel',
  isDangerous = false,
}: {
  isOpen: boolean
  onClose: () => void
  onConfirm: () => void
  title: string
  description: string
  confirmText?: string
  cancelText?: string
  isDangerous?: boolean
}) {
  return (
    <Modal isOpen={isOpen} onClose={onClose} title={title} size="sm">
      <p className="text-slate-300 mb-6">{description}</p>
      <div className="flex gap-3 justify-end">
        <Button variant="secondary" onClick={onClose}>
          {cancelText}
        </Button>
        <Button variant={isDangerous ? 'danger' : 'primary'} onClick={onConfirm}>
          {confirmText}
        </Button>
      </div>
    </Modal>
  )
}
