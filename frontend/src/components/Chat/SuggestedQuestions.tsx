import { Button } from '@/components/ui'

interface SuggestedQuestionsProps {
  questions: string[]
  onSelect: (question: string) => void
}

export default function SuggestedQuestions({ questions, onSelect }: SuggestedQuestionsProps) {
  return (
    <div className="space-y-3">
      <p className="text-label text-ink-muted">Suggested Questions</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {questions.map((q, idx) => (
          <Button key={idx} onClick={() => onSelect(q)} variant="secondary" className="w-full text-left text-sm justify-start">
            {q}
          </Button>
        ))}
      </div>
    </div>
  )
}
