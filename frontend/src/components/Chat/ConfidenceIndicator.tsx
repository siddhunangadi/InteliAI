import { AlertCircle, CheckCircle } from 'lucide-react'
import { Card } from '@/components/ui'

interface ConfidenceIndicatorProps {
  score: number
}

// Confidence describes retrieval/verification outcome, so it is one of the
// few places the reserved status colors (DESIGN.md Status-Means-Something
// Rule) are allowed outside Health/Audit.
// Tailwind's compiler needs literal class strings, not interpolated ones --
// each status gets its own fully-spelled class set.
const styles = {
  verified: { card: 'bg-status-verified/10 border-status-verified/30', text: 'text-status-verified' },
  caution: { card: 'bg-status-caution/10 border-status-caution/30', text: 'text-status-caution' },
  critical: { card: 'bg-status-critical/10 border-status-critical/30', text: 'text-status-critical' },
} as const

export default function ConfidenceIndicator({ score }: ConfidenceIndicatorProps) {
  const level = score > 0.8 ? 'High' : score > 0.6 ? 'Medium' : 'Low'
  const status = score > 0.8 ? 'verified' : score > 0.6 ? 'caution' : 'critical'

  const reasons: Record<string, string> = {
    High: 'Multiple current regulations support this answer.',
    Medium: 'Some regulations support this answer with minor uncertainties.',
    Low: 'Limited evidence supports this answer. Verify with compliance team.',
  }

  return (
    <Card className={styles[status].card}>
      <div className="flex items-start gap-2">
        <div className={styles[status].text}>
          {level === 'High' ? <CheckCircle className="w-4 h-4" /> : <AlertCircle className="w-4 h-4" />}
        </div>
        <div>
          <p className={`text-sm font-medium ${styles[status].text}`}>Confidence: {level}</p>
          <p className="text-label text-ink-muted mt-1">{reasons[level]}</p>
        </div>
      </div>
    </Card>
  )
}
