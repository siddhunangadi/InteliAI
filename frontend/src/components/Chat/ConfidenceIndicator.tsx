import { useState } from 'react'
import { AlertTriangle, CheckCircle, AlertCircle, ChevronDown } from 'lucide-react'
import { Card } from '@/components/ui'
import { ConfidenceMetrics } from '@/lib/types'

interface ConfidenceIndicatorProps {
  confidence: ConfidenceMetrics
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

// Below this, retrieval didn't find anything genuinely relevant -- the
// model may still have generated a grammatical answer, but there's no real
// evidence behind it. Distinct from "Low confidence": this says the corpus
// doesn't cover the question at all.
const NO_EVIDENCE_THRESHOLD = 0.35

const pct = (n: number) => `${Math.round(n * 100)}%`

export default function ConfidenceIndicator({ confidence }: ConfidenceIndicatorProps) {
  const [expanded, setExpanded] = useState(false)
  const { overall, retrieval, citations, coverage } = confidence

  if (retrieval < NO_EVIDENCE_THRESHOLD) {
    return (
      <Card className={styles.critical.card}>
        <div className="flex items-start gap-2">
          <AlertTriangle className={`w-4 h-4 flex-shrink-0 mt-0.5 ${styles.critical.text}`} />
          <div>
            <p className={`text-sm font-medium ${styles.critical.text}`}>No relevant passages found</p>
            <p className="text-label text-ink-muted mt-1">
              The indexed documents don't appear to cover this question.
            </p>
            <p className="text-label text-ink-muted mt-1">Top retrieval score: {pct(retrieval)}</p>
          </div>
        </div>
      </Card>
    )
  }

  const level = overall > 0.8 ? 'High' : overall > 0.6 ? 'Medium' : 'Low'
  const status = overall > 0.8 ? 'verified' : overall > 0.6 ? 'caution' : 'critical'
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
        <div className="flex-1">
          <div className="flex items-center justify-between gap-2">
            <p className={`text-sm font-medium ${styles[status].text}`}>
              Confidence: {pct(overall)}
              <span className="text-ink-muted font-normal"> · {level}</span>
            </p>
            <button
              type="button"
              onClick={() => setExpanded((v) => !v)}
              className="text-label text-ink-muted hover:text-ink flex items-center gap-0.5"
            >
              Details
              <ChevronDown className={`w-3 h-3 transition-transform duration-150 ${expanded ? 'rotate-180' : ''}`} />
            </button>
          </div>
          <p className="text-label text-ink-muted mt-1">{reasons[level]}</p>

          <div
            className="overflow-hidden transition-[max-height] duration-[120ms] ease-out"
            style={{ maxHeight: expanded ? '6rem' : 0 }}
          >
            <div className="grid grid-cols-3 gap-2 mt-3 pt-3 border-t border-rule/60">
              <div>
                <p className="text-mono-data text-ink">{pct(retrieval)}</p>
                <p className="text-label text-ink-muted">Retrieval</p>
              </div>
              <div>
                <p className="text-mono-data text-ink">{pct(citations)}</p>
                <p className="text-label text-ink-muted">Citations verified</p>
              </div>
              <div>
                <p className="text-mono-data text-ink">{pct(coverage)}</p>
                <p className="text-label text-ink-muted">Source coverage</p>
              </div>
            </div>
          </div>
        </div>
      </div>
    </Card>
  )
}
