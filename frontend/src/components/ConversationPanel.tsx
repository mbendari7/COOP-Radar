/**
 * The AI helper for one matched job.
 *
 *   one click to tailor the resume or write a cover letter opener
 *   Ask a question opens a free text box and answers point back to the resume or the job
 *   replies stream in word by word and each one can be copied
 *   with no AI key it points people to the AI key page instead
 */

import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useAiKey } from '../api/aiKey'
import { usePublicConfig } from '../api/meta'
import { askAboutPosting, type AskMode } from '../api/resume'
import RichText from './RichText'

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

const ACTION_LABELS: Record<Exclude<AskMode, 'question'>, string> = {
  tailor: 'How should I tailor my resume for this job?',
  cover_letter: 'Write a cover letter opener for this job.',
}

function CopyButton({ text }: { text: string }) {
  const [copied, setCopied] = useState(false)
  return (
    <button
      type="button"
      onClick={() => {
        void navigator.clipboard?.writeText(text).then(() => {
          setCopied(true)
          setTimeout(() => setCopied(false), 1500)
        })
      }}
      className="text-xs font-semibold text-gray-700 hover:text-gray-900 hover:underline"
    >
      {copied ? 'Copied' : 'Copy'}
    </button>
  )
}

export default function ConversationPanel({ postingId, postingTitle, company }: Props) {
  const aiKey = useAiKey()
  const { data: config } = usePublicConfig()
  const canUseAi = Boolean(aiKey) || Boolean(config?.server_ai_enabled)

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

  async function run(mode: AskMode, question: string) {
    if (loading) return
    setOpen(true)
    setError(null)
    setMessages((prev) => [
      ...prev,
      { role: 'user', text: mode === 'question' ? question : ACTION_LABELS[mode] },
      { role: 'assistant', text: '', streaming: true },
    ])
    setLoading(true)

    await askAboutPosting(
      postingId,
      question,
      (delta) => {
        setMessages((prev) => {
          const next = [...prev]
          const last = next[next.length - 1]
          if (last?.role === 'assistant') next[next.length - 1] = { ...last, text: last.text + delta }
          return next
        })
      },
      () => {
        setMessages((prev) => prev.map((m) => (m.streaming ? { ...m, streaming: false } : m)))
        setLoading(false)
        setTimeout(() => inputRef.current?.focus(), 50)
      },
      (err) => {
        setError(err.message)
        setMessages((prev) => prev.filter((m) => !m.streaming))
        setLoading(false)
      },
      mode,
    )
  }

  function handleSend() {
    const q = input.trim()
    if (!q) return
    setInput('')
    void run('question', q)
  }

  const actionClass = 'btn-secondary px-3 py-1.5 font-semibold'

  if (!canUseAi) {
    return (
      <p className="text-sm text-gray-700">
        <Link to="/ai-key" className="link">Add a free AI key</Link>{' '}
        to tailor your resume, draft a cover letter opener, or ask questions about this job.
      </p>
    )
  }

  return (
    <div>
      <div className="flex flex-wrap gap-2">
        <button type="button" disabled={loading} onClick={() => void run('tailor', '')} className={actionClass}>
          Tailor my resume for this job
        </button>
        <button type="button" disabled={loading} onClick={() => void run('cover_letter', '')} className={actionClass}>
          Write a cover letter opener
        </button>
        <button
          type="button"
          onClick={() => (open ? handleClose() : setOpen(true))}
          className="btn-quiet px-3 py-1.5"
          aria-expanded={open}
          aria-controls={`conversation-${postingId}`}
        >
          {open ? 'Close' : 'Ask a question'}
        </button>
      </div>

      {open && (
        <div
          id={`conversation-${postingId}`}
          className="mt-3 space-y-3 border-[1.5px] border-gray-900 bg-gray-50 p-4"
          aria-label={`AI assistant for ${postingTitle} at ${company}`}
        >
          {messages.length > 0 && (
            <div className="max-h-[28rem] space-y-4 overflow-y-auto" role="log" aria-live="polite">
              {messages.map((msg, i) => (
                <div key={i} className="text-sm">
                  {msg.role === 'user' ? (
                    <p className="font-semibold text-gray-900">
                      <span className="label-form mb-0.5 block">You</span>
                      {msg.text}
                    </p>
                  ) : (
                    <div className="text-gray-800">
                      <div className="mb-0.5 flex items-center justify-between">
                        <span className="label-form !text-air-700">{msg.streaming ? 'Writing...' : 'Assistant'}</span>
                        {!msg.streaming && msg.text && <CopyButton text={msg.text} />}
                      </div>
                      <RichText text={msg.text} />
                      {msg.streaming && msg.text === '' && (
                        <span className="inline-block h-4 w-2 animate-pulse bg-gray-400" aria-hidden="true" />
                      )}
                    </div>
                  )}
                </div>
              ))}
            </div>
          )}

          {error && <p role="alert" className="text-sm font-semibold text-post-700">{error}</p>}

          <div className="flex items-end gap-2">
            <label htmlFor={`qa-input-${postingId}`} className="sr-only">
              Ask a question about this role
            </label>
            <textarea
              ref={inputRef}
              id={`qa-input-${postingId}`}
              rows={2}
              value={input}
              onChange={(e) => setInput(e.target.value)}
              onKeyDown={(e) => {
                if (e.key === 'Enter' && !e.shiftKey) {
                  e.preventDefault()
                  handleSend()
                }
              }}
              placeholder="For example, do I have the skills for this role?"
              disabled={loading}
              className="field flex-1 resize-none"
            />
            <button
              onClick={handleSend}
              disabled={!input.trim() || loading}
              className="btn-primary shrink-0"
            >
              {loading ? '...' : 'Send'}
            </button>
          </div>
          <p className="text-xs text-gray-600">
            Answers use only your resume and this posting. Always check before you send anything.
          </p>
        </div>
      )}
    </div>
  )
}
