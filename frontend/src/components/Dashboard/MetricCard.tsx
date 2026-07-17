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
