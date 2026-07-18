import { useState, useRef, useEffect } from 'react'
import { isAxiosError } from 'axios'
import { Send } from 'lucide-react'
import { apiClient } from '@/lib/api'
import { StructuredCitation, RagAnswer } from '@/lib/types'
import { Card } from '@/components/ui'
import ChatMessage from '@/components/Chat/ChatMessage'
import SuggestedQuestions from '@/components/Chat/SuggestedQuestions'

interface Message {
  id: string
  role: 'user' | 'assistant'
  content: string
  citations?: StructuredCitation[]
  confidenceScore?: number
  streaming?: boolean
  timestamp: Date
}

const EXAMPLE_QUESTIONS = [
  'What are the latest RBI KYC requirements?',
  'Show the current SEBI cyber security regulations',
  'Has GST input tax credit changed recently?',
  'Which regulations affect NBFC lending?',
]

// Parses the `event: <type>\ndata: <json>\n\n` SSE frames emitted by
// POST /answer/stream (see api/routes.py answer_stream). apiClient.answerStream
// yields raw decoded text chunks, which may split a frame across chunks, so
// this buffers and only emits on a complete blank-line-terminated frame.
function parseSSE(buffer: string): { events: { type: string; data: string }[]; rest: string } {
  const events: { type: string; data: string }[] = []
  const frames = buffer.split('\n\n')
  const rest = frames.pop() ?? ''
  for (const frame of frames) {
    const typeLine = frame.split('\n').find((l) => l.startsWith('event: '))
    const dataLine = frame.split('\n').find((l) => l.startsWith('data: '))
    if (typeLine && dataLine) {
      events.push({ type: typeLine.slice(7), data: dataLine.slice(6) })
    }
  }
  return { events, rest }
}

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
    const assistantId = Math.random().toString(36)
    setMessages((prev) => [
      ...prev,
      userMessage,
      { id: assistantId, role: 'assistant', content: '', streaming: true, timestamp: new Date() },
    ])
    setInput('')
    setError(undefined)
    setLoading(true)

    try {
      let buffer = ''
      for await (const chunk of apiClient.answerStream({ question: userMessage.content, top_k: 5 })) {
        buffer += chunk
        const { events, rest } = parseSSE(buffer)
        buffer = rest
        for (const evt of events) {
          if (evt.type === 'delta') {
            const { text } = JSON.parse(evt.data) as { text: string }
            setMessages((prev) =>
              prev.map((m) => (m.id === assistantId ? { ...m, content: m.content + text } : m))
            )
          } else if (evt.type === 'final') {
            const final = JSON.parse(evt.data) as RagAnswer
            setMessages((prev) =>
              prev.map((m) =>
                m.id === assistantId
                  ? {
                      ...m,
                      content: final.answer,
                      citations: final.structured_citations,
                      confidenceScore: final.confidence.overall,
                      streaming: false,
                    }
                  : m
              )
            )
          }
        }
      }
    } catch (err) {
      setMessages((prev) => prev.filter((m) => m.id !== assistantId))
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
        <div className="flex-1 flex flex-col items-center justify-center">
          <div className="max-w-2xl w-full space-y-8">
            <div className="text-center">
              <h1 className="text-display text-ink mb-2">Ask</h1>
              <p className="text-ink-muted">
                Ask questions about regulatory requirements, compliance changes, and policy interpretations
              </p>
            </div>

            <SuggestedQuestions questions={EXAMPLE_QUESTIONS} onSelect={(q) => setInput(q)} />
          </div>
        </div>
      ) : (
        <div className="flex-1 overflow-y-auto space-y-4 mb-6">
          {messages.map((msg) => (
            <ChatMessage key={msg.id} {...msg} />
          ))}
          <div ref={messagesEndRef} />
        </div>
      )}

      {error && (
        <Card className="bg-status-critical/10 border-status-critical/30 mb-4">
          <p className="text-status-critical text-sm">{error}</p>
        </Card>
      )}

      <form onSubmit={handleSubmit} className="flex gap-2">
        <input
          type="text"
          value={input}
          onChange={(e) => setInput(e.target.value)}
          placeholder="Ask about regulations, compliance requirements..."
          className="input flex-1"
          disabled={loading}
        />
        <button type="submit" className="btn btn-primary" disabled={loading || !input.trim()}>
          <Send className="w-4 h-4" />
        </button>
      </form>
    </div>
  )
}
