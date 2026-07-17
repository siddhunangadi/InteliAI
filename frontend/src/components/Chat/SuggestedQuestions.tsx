import { Button } from '@/components/ui'
import { motion } from 'framer-motion'

interface SuggestedQuestionsProps {
  questions: string[]
  onSelect: (question: string) => void
}

export default function SuggestedQuestions({ questions, onSelect }: SuggestedQuestionsProps) {
  return (
    <div className="space-y-3">
      <p className="text-sm font-medium text-slate-400">Suggested Questions</p>
      <div className="grid grid-cols-1 md:grid-cols-2 gap-2">
        {questions.map((q, idx) => (
          <motion.div
            key={idx}
            initial={{ opacity: 0, y: 10 }}
            animate={{ opacity: 1, y: 0 }}
            transition={{ delay: idx * 0.05 }}
          >
            <Button
              onClick={() => onSelect(q)}
              variant="secondary"
              className="w-full text-left text-sm"
            >
              {q}
            </Button>
          </motion.div>
        ))}
      </div>
    </div>
  )
}
