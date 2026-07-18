import { InputHTMLAttributes, ReactNode } from 'react'
import clsx from 'clsx'

interface InputProps extends InputHTMLAttributes<HTMLInputElement> {
  label?: string
  error?: string
  icon?: ReactNode
  hint?: string
}

export function Input({ label, error, icon, hint, className, id, ...props }: InputProps) {
  const inputId = id || `input-${Math.random()}`

  return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={inputId} className="block text-label text-ink-muted">
          {label}
        </label>
      )}
      <div className="relative">
        {icon && <div className="absolute left-3 top-3 text-ink-muted">{icon}</div>}
        <input
          id={inputId}
          className={clsx('input', icon && 'pl-10', error && 'input-error', className)}
          {...props}
        />
      </div>
      {error && <p className="text-label text-status-critical">{error}</p>}
      {hint && !error && <p className="text-label text-ink-muted">{hint}</p>}
    </div>
  )
}

export function Textarea({ label, error, hint, className, id, ...props }: Omit<InputProps, 'icon'> & React.TextareaHTMLAttributes<HTMLTextAreaElement>) {
  const inputId = id || `textarea-${Math.random()}`

  return (
    <div className="space-y-1">
      {label && (
        <label htmlFor={inputId} className="block text-label text-ink-muted">
          {label}
        </label>
      )}
      <textarea
        id={inputId}
        className={clsx('input resize-none', error && 'input-error', className)}
        {...props}
      />
      {error && <p className="text-label text-status-critical">{error}</p>}
      {hint && !error && <p className="text-label text-ink-muted">{hint}</p>}
    </div>
  )
}
