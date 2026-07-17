import { AlertCircle, CheckCircle } from 'lucide-react'
import { Card } from '@/components/ui'

interface ConfidenceIndicatorProps {
  score: number
}

export default function ConfidenceIndicator({ score }: ConfidenceIndicatorProps) {
  const level = score > 0.8 ? 'High' : score > 0.6 ? 'Medium' : 'Low'
  const colorClass = score > 0.8 ? 'emerald' : score > 0.6 ? 'yellow' : 'red'
  const icon = score > 0.8 ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />

  const reasons: Record<string, string> = {
    High: 'Multiple current regulations support this answer.',
    Medium: 'Some regulations support this answer with minor uncertainties.',
    Low: 'Limited evidence supports this answer. Verify with compliance team.',
  }

  const bgColorMap: Record<string, string> = {
    emerald: 'bg-emerald-500/10',
    yellow: 'bg-yellow-500/10',
    red: 'bg-red-500/10',
  }

  const borderColorMap: Record<string, string> = {
    emerald: 'border-emerald-500/30',
    yellow: 'border-yellow-500/30',
    red: 'border-red-500/30',
  }

  const textColorMap: Record<string, string> = {
    emerald: 'text-emerald-400',
    yellow: 'text-yellow-400',
    red: 'text-red-400',
  }

  return (
    <Card className={`${bgColorMap[colorClass]} border ${borderColorMap[colorClass]}`}>
      <div className="flex items-start gap-2">
        <div className={textColorMap[colorClass]}>{icon}</div>
        <div>
          <p className={`text-sm font-medium ${textColorMap[colorClass]}`}>
            Confidence: {level}
          </p>
          <p className="text-xs text-slate-400 mt-1">{reasons[level]}</p>
        </div>
      </div>
    </Card>
  )
}
