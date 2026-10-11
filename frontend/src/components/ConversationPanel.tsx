/**
 * ConversationPanel — inline Q&A panel for a single match card.
 *
 * - "Ask about this role" button toggles the panel
 * - Free-text question input streams the response word-by-word
 * - Citation prefixes "Resume: " and "Posting: " are bolded
 * - Clears conversation on close
 */

import { useRef, useState } from 'react'
import { askAboutPosting } from '../api/resume'

interface Props {
  postingId: string
  postingTitle: string
  company: string
}

interface Message {
  role: 'user' | 'assistant'
  text: string
  streaming?: boolean
}

/** Bold "Resume: " and "Posting: " citation prefixes within a text string */
function CitedText({ text }: { text: string }) {
  const parts = text.split(/((?:Resume|Posting):\s)/g)
  return (
    <>
      {parts.map((part, i) =>
        /^(?:Resume|Posting):\s$/.test(part)
          ? <strong key={i}>{part}</strong>
          : <span key={i}>{part}</span>
      )}
    </>
  )
}

export default function ConversationPanel({ postingId, postingTitle, company }: Props) {
  const [open, setOpen] = useState(false)
  const [messages, setMessages] = useState<Message[]>([])
  const [input, setInput] = useState('')
  const [loading, setLoading] = useState(false)
  const [error, setError] = useState<string | null>(null)
  const inputRef = useRef<HTMLTextAreaElement>(null)

  function handleClose() {
    setOpen(false)
    setMessages([])
    setInput('')
    setError(null)
  }

  async function handleSend() {
    const q = input.trim()
    if (!q || loading) return

    setInput('')
    setError(null)
    setMessages((prev) => [...prev, { role: 'user', text: q }])
    setLoading(true)

    // Add a streaming assistant message placeholder
    setMessages((prev) => [...prev, { role: 'assistant', text: '', streaming: true }])

    await askAboutPosting(
      postingId,
      q,
      (delta) => {
        setMessages((prev) => {
          const next = [...prev]
          const last = next[next.length - 1]
          if (last?.role === 'assistant') {
            next[next.length - 1] = { ...last, text: last.text + delta }
          }
          return next
        })
      },
      () => {
        setMessages((prev) => {
          const next = [...prev]
          const last = next[next.length - 1]
          if (last?.role === 'assistant') {
            next[next.length - 1] = { ...last, streaming: false }
          }
          return next
        })
        setLoading(false)
        setTimeout(() => inputRef.current?.focus(), 50)
      },
      (err) => {
        setError(err.message)
        setMessages((prev) => prev.filter((m) => !m.streaming))
        setLoading(false)
      },
    )
  }

  function handleKeyDown(e: React.KeyboardEvent<HTMLTextAreaElement>) {
    if (e.key === 'Enter' && !e.shiftKey) {
      e.preventDefault()
      void handleSend()
    }
  }

  return (
    <div>
      {/* Toggle button */}
      <button
        onClick={() => (open ? handleClose() : setOpen(true))}
        className="mt-3 text-sm text-brand-600 hover:underline focus:outline-none focus:ring-2 focus:ring-brand-500 rounded"
        aria-expanded={open}
        aria-controls={`conversation-${postingId}`}
      >
        {open ? 'Close conversation' : 'Ask about this role'}
      </button>

      {/* Inline panel */}
      {open && (
        <div
          id={`conversation-${postingId}`}
          className="mt-3 rounded-lg border border-gray-200 bg-gray-50 p-4 space-y-3"
          aria-label={`Q&A for ${postingTitle} at ${company}`}
        >
          {/* Context label */}
          <p className="text-xs text-gray-500 font-medium">
            Asking about: <span className="text-gray-700">{postingTitle}</span> at {company}
          </p>

          {/* Message history */}
          {messages.length > 0 && (
            <div className="space-y-3 max-h-80 overflow-y-auto" role="log" aria-live="polite">
              {messages.map((msg, i) => (
                <div
                  key={i}
                  className={`text-sm ${msg.role === 'user' ? 'text-gray-800 font-medium' : 'text-gray-700'}`}
                >
                  {msg.role === 'user' && (
                    <span className="text-xs text-gray-400 block mb-0.5">You</span>
                  )}
                  {msg.role === 'assistant' && (
                    <span className="text-xs text-gray-400 block mb-0.5">
                      {msg.streaming ? 'Thinking…' : 'Assistant'}
                    </span>
                  )}
                  {msg.role === 'assistant'
                    ? <CitedText text={msg.text} />
                    : msg.text
                  }
                  {msg.streaming && msg.text === '' && (
                    <span className="inline-block w-2 h-4 bg-gray-400 animate-pulse ml-0.5" aria-hidden="true" />
                  )}
                </div>
              ))}
            </div>
          )}

          {/* Error */}
          {error && (
            <p role="alert" className="text-sm text-red-600">{error}</p>
          )}

          {/* Input row */}
          <div className="flex gap-2 items-end">
            <label htmlFor={`qa-input-${postingId}`} className="sr-only">
              Ask a question about this role
            </label>
            <textarea
              ref={inputRef}
              id={`qa-input-${postingId}`}
              rows={2}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={handleKeyDown}
              placeholder="e.g. What Python skills match this role?"
              disabled={loading}
              className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm resize-none focus:outline-none focus:ring-2 focus:ring-brand-500 disabled:opacity-50"
            />
            <button
              onClick={() => void handleSend()}
              disabled={!input.trim() || loading}
              className="shrink-0 px-4 py-2 rounded-lg bg-brand-600 text-white text-sm font-medium hover:bg-brand-700 disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {loading ? '…' : 'Send'}
            </button>
          </div>

          <p className="text-xs text-gray-400">
            Press Enter to send, Shift+Enter for a new line.
          </p>
        </div>
      )}
    </div>
  )
}
