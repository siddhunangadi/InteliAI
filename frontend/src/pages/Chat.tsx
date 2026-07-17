import { useState, useRef, useEffect } from 'react'
import { isAxiosError } from 'axios'
import { Send, Loader } from 'lucide-react'
import { motion } from 'framer-motion'
import { apiClient } from '@/lib/api'
import { StructuredCitation } from '@/lib/types'
import { Card, Button } from '@/components/ui'
import ChatMessage from '@/components/Chat/ChatMessage'
import SuggestedQuestions from '@/components/Chat/SuggestedQuestions'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: StructuredCitation[]
  confidenceScore?: number
  timestamp: Date
}

const EXAMPLE_QUESTIONS = [
  'What are the latest RBI KYC requirements?',
  'Show the current SEBI cyber security regulations',
  'Has GST input tax credit changed recently?',
  'Which regulations affect NBFC lending?',
]

export default function Chat() {
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string>()
  const messagesEndRef = useRef<HTMLDivElement>(null)

  useEffect(() => {
    messagesEndRef.current?.scrollIntoView({ behavior: 'smooth' })
  }, [messages])

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    if (!input.trim()) return

    const userMessage: Message = {
      id: Math.random().toString(36),
      role: 'user',
      content: input,
      timestamp: new Date(),
    }
    setMessages(prev => [...prev, userMessage])
    setInput('')
    setError(undefined)
    setLoading(true)

    try {
      const response = await apiClient.answer({
        question: input,
        top_k: 5,
      })

      const assistantMessage: Message = {
        id: Math.random().toString(36),
        role: 'assistant',
        content: response.answer,
        citations: response.structured_citations,
        confidenceScore: response.confidence.overall,
        timestamp: new Date(),
      }
      setMessages(prev => [...prev, assistantMessage])
    } catch (err) {
      if (isAxiosError(err) && err.response?.status === 401) {
        setError('Your API key is missing or invalid. Add it in Settings to use the AI Assistant.')
      } else {
        setError(err instanceof Error ? err.message : 'Unable to generate answer')
      }
    } finally {
      setLoading(false)
    }
  }

  return (
    <div className="flex flex-col h-[calc(100vh-120px)]">
      {messages.length === 0 ? (
        <motion.div
          initial={{ opacity: 0, y: 20 }}
          animate={{ opacity: 1, y: 0 }}
          className="flex-1 flex flex-col items-center justify-center"
        >
          <div className="max-w-2xl w-full space-y-8">
            <div className="text-center">
              <h1 className="text-3xl font-bold mb-2">AI Compliance Assistant</h1>
              <p className="text-slate-400">
                Ask questions about regulatory requirements, compliance changes, and policy interpretations
              </p>
            </div>

            <SuggestedQuestions
              questions={EXAMPLE_QUESTIONS}
              onSelect={q => setInput(q)}
            />
          </div>
        </motion.div>
      ) : (
        <div className="flex-1 overflow-y-auto space-y-4 mb-6">
          {messages.map(msg => (
            <ChatMessage key={msg.id} {...msg} />
          ))}
          {loading && (
            <motion.div
              initial={{ opacity: 0 }}
              animate={{ opacity: 1 }}
              className="flex items-center gap-2"
            >
              <Loader className="w-4 h-4 animate-spin text-blue-400" />
              <span className="text-sm text-slate-400">Analyzing regulations...</span>
            </motion.div>
          )}
          <div ref={messagesEndRef} />
        </div>
      )}

      {error && (
        <Card className="bg-red-500/10 border-red-500/30 mb-4">
          <p className="text-red-400 text-sm">{error}</p>
        </Card>
      )}

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={e => setInput(e.target.value)}
          placeholder="Ask about regulations, compliance requirements..."
          className="flex-1 px-4 py-2.5 bg-slate-800 border border-slate-700 rounded-lg text-slate-100 placeholder-slate-500 focus:outline-none focus:border-blue-500"
          disabled={loading}
        />
        <Button type="submit" disabled={loading || !input.trim()}>
          <Send className="w-4 h-4" />
        </Button>
      </form>
    </div>
  )
}
