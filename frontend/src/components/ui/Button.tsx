import { ButtonHTMLAttributes, ReactNode } from 'react'
import clsx from 'clsx'

interface ButtonProps extends ButtonHTMLAttributes<HTMLButtonElement> {
  variant?: 'primary' | 'secondary' | 'danger'
  size?: 'sm' | 'md' | 'lg'
  icon?: ReactNode
  iconPosition?: 'left' | 'right'
  isLoading?: boolean
}

// DESIGN.md: only primary/secondary exist -- "no tertiary/ghost variant
// beyond this to avoid button-hierarchy sprawl." Danger reuses
// status-critical for destructive confirms (delete document, etc).
const variantClasses = {
  primary: 'btn-primary',
  secondary: 'btn-secondary',
  danger: 'bg-status-critical hover:bg-status-critical/85 text-void',
}

const sizeClasses = {
  sm: 'px-3 py-1.5 text-sm',
  md: '',
  lg: 'px-6 py-3 text-base',
}

export function Button({
  variant = 'primary',
  size = 'md',
  icon,
  iconPosition = 'left',
  isLoading,
  children,
  className,
  disabled,
  ...props
}: ButtonProps) {
  return (
    <button
      className={clsx('btn', variantClasses[variant], sizeClasses[size], className)}
      disabled={disabled || isLoading}
      {...props}
    >
      {isLoading && (
        <svg className="animate-spin -ml-1 mr-2 h-4 w-4" xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24">
          <circle className="opacity-25" cx="12" cy="12" r="10" stroke="currentColor" strokeWidth="4" />
          <path className="opacity-75" fill="currentColor" d="M4 12a8 8 0 018-8V0C5.373 0 0 5.373 0 12h4zm2 5.291A7.962 7.962 0 014 12H0c0 3.042 1.135 5.824 3 7.938l3-2.647z" />
        </svg>
      )}
      {icon && iconPosition === 'left' && !isLoading && <span className="mr-2">{icon}</span>}
      {children}
      {icon && iconPosition === 'right' && <span className="ml-2">{icon}</span>}
    </button>
  )
}

export function IconButton({
  icon,
  variant = 'secondary',
  size = 'md',
  ...props
}: Omit<ButtonProps, 'children'> & { icon: ReactNode }) {
  return (
    <Button
      variant={variant}
      size={size}
      {...props}
      className={clsx('aspect-square', props.className)}
    >
      {icon}
    </Button>
  )
}
