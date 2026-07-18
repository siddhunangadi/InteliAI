import { ReactNode } from 'react'
import { TrendingUp, TrendingDown } from 'lucide-react'
import clsx from 'clsx'

interface CardProps {
  children: ReactNode
  className?: string
  interactive?: boolean
}

// DESIGN.md Cards: Panel bg, 1px Seam border all sides, 10px radius, no
// shadow at rest (Flat-at-Rest Rule) -- separation comes from the border only.
export function Card({ children, className, interactive }: CardProps) {
  return (
    <div
      className={clsx(
        'card',
        interactive && 'hover:bg-panel-raised transition-colors duration-150 cursor-pointer',
        className
      )}
    >
      {children}
    </div>
  )
}

// Canonical MetricCard (was duplicated in components/Dashboard/MetricCard.tsx).
// DESIGN.md: stat tiles are a supporting player, not the hero -- keep small.
export function MetricCard({ label, value, unit, trend }: {
  label: string
  value: string | number
  unit?: string
  trend?: { direction: 'up' | 'down'; percent: number }
}) {
  return (
    <Card>
      <p className="text-label text-ink-muted">{label}</p>
      <div className="flex items-end gap-2 mt-2">
        <p className="text-2xl font-semibold tracking-tighter text-ink">{value}</p>
        {unit && <p className="text-label text-ink-muted mb-0.5">{unit}</p>}
      </div>
      {trend && (
        <div className="mt-2 flex items-center gap-1 text-label">
          {trend.direction === 'up' ? (
            <TrendingUp className="w-3.5 h-3.5 text-ink-muted" />
          ) : (
            <TrendingDown className="w-3.5 h-3.5 text-ink-muted" />
          )}
          <span className="text-ink-muted">{trend.percent}%</span>
        </div>
      )}
    </Card>
  )
}

// Health/status summary tile. Uses the reserved status colors -- outcome only.
export function StatusCard({ status, label, details }: {
  status: 'healthy' | 'warning' | 'error'
  label: string
  details?: string
}) {
  const statusColor = {
    healthy: 'text-status-verified',
    warning: 'text-status-caution',
    error: 'text-status-critical',
  }
  const dotColor = {
    healthy: 'bg-status-verified',
    warning: 'bg-status-caution',
    error: 'bg-status-critical',
  }

  return (
    <div className="card">
      <div className="flex items-center gap-2">
        <div className={clsx('w-2 h-2 rounded-full', dotColor[status])} />
        <span className={clsx('text-label', statusColor[status])}>{label}</span>
      </div>
      {details && <p className="text-label text-ink-muted mt-1">{details}</p>}
    </div>
  )
}
