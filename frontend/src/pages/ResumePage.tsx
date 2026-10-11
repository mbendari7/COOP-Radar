/**
 * ResumePage — /resume, the heart of CoopRadar.
 *
 *   1. Upload a resume (no account needed: a private temporary account is created)
 *   2. What it shows — skills found, and in-demand skills it's missing (free, no AI)
 *      + an AI review: strengths, fixes, tailoring tips, roles to search (visitor's own key)
 *   3. Jobs to apply for — ranked matches, each with "Tailor my resume" / "Cover letter opener"
 */

import { useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { providerName, useAiKey } from '../api/aiKey'
import { guestLogin, useMe } from '../api/auth'
import { ApiError } from '../api/client'
import { usePublicConfig } from '../api/meta'
import {
  useDeleteResume,
  useGenerateInsights,
  useInsights,
  useMatches,
  useRematch,
  useUploadResume,
  type AIInsights,
  type MatchResultOut,
  type ResumeOut,
} from '../api/resume'
import AuthModal from '../components/AuthModal'
import ConversationPanel from '../components/ConversationPanel'
import { formatDate, formatLocation } from '../utils/format'

const MAX_SIZE_BYTES = 5 * 1024 * 1024

function useCanUseAi(): boolean {
  const aiKey = useAiKey()
  const { data: config } = usePublicConfig()
  return Boolean(aiKey) || Boolean(config?.server_ai_enabled)
}

// ── Step 1: upload ────────────────────────────────────────────────────────────

function ResumeDropzone({ compact }: { compact: boolean }) {
  const { data: me } = useMe()
  const { data: config } = usePublicConfig()
  const qc = useQueryClient()
  const upload = useUploadResume()
  const inputRef = useRef<HTMLInputElement>(null)
  const [error, setError] = useState<string | null>(null)
  const [dragging, setDragging] = useState(false)
  const [starting, setStarting] = useState(false)
  const [authOpen, setAuthOpen] = useState(false)

  async function handleFile(file: File | undefined) {
    if (!file) return
    setError(null)
    const ext = file.name.split('.').pop()?.toLowerCase()
    if (ext !== 'pdf' && ext !== 'docx') {
      setError('Please upload a PDF or Word (.docx) file.')
      return
    }
    if (file.size > MAX_SIZE_BYTES) {
      setError('That file is over 5 MB. Try exporting a smaller PDF.')
      return
    }
    if (!me) {
      if (config && !config.demo_enabled) {
        setAuthOpen(true)
        return
      }
      setStarting(true)
      try {
        const user = await guestLogin()
        qc.setQueryData(['me'], user)
      } catch (err) {
        setStarting(false)
        if (err instanceof ApiError && err.code === 'DEMO_DISABLED') {
          setAuthOpen(true)  // this site requires an account
        } else {
          setError(err instanceof Error ? err.message : 'Could not start. Please try again.')
        }
        return
      }
      setStarting(false)
    }
    upload.mutate(file, {
      onSuccess: () => {
        if (inputRef.current) inputRef.current.value = ''
      },
      onError: (err) => setError(err.message || 'Upload failed.'),
    })
  }

  const busy = starting || upload.isPending

  return (
    <div>
      <label
        htmlFor="resume-file"
        onDragOver={(e) => { e.preventDefault(); setDragging(true) }}
        onDragLeave={() => setDragging(false)}
        onDrop={(e) => {
          e.preventDefault()
          setDragging(false)
          void handleFile(e.dataTransfer.files?.[0])
        }}
        className={`block cursor-pointer rounded-2xl border-2 border-dashed text-center transition-colors ${
          compact ? 'p-4' : 'p-10'
        } ${dragging ? 'border-blue-500 bg-blue-50' : 'border-gray-300 bg-white hover:border-blue-400 hover:bg-blue-50/40'}`}
      >
        {busy ? (
          <span className="block text-blue-700 font-medium animate-pulse">
            Reading your resume and matching it to open jobs…
          </span>
        ) : compact ? (
          <span className="text-sm text-gray-700">
            <span className="font-semibold text-blue-700">Upload a new version</span> — drop a PDF or DOCX here
          </span>
        ) : (
          <>
            <span className="block text-4xl" aria-hidden="true">📄</span>
            <span className="mt-2 block text-lg font-semibold text-gray-900">
              Drop your resume here, or <span className="text-blue-700 underline">browse</span>
            </span>
            <span className="mt-1 block text-sm text-gray-500">PDF or Word (.docx), up to 5 MB · no sign-up needed</span>
          </>
        )}
        <input
          ref={inputRef}
          id="resume-file"
          type="file"
          accept=".pdf,.docx"
          className="sr-only"
          disabled={busy}
          onChange={(e) => void handleFile(e.target.files?.[0])}
        />
      </label>
      {error && <p role="alert" className="mt-2 text-sm text-red-600">{error}</p>}
      {!compact && (
        <p className="mt-2 text-xs text-gray-500">
          Your resume is stored privately in your account and is only sent to the AI you choose. Delete it any time.
        </p>
      )}
      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} initialTab="register" />
    </div>
  )
}

function StoredResume({ resume }: { resume: ResumeOut }) {
  const del = useDeleteResume()
  const [confirm, setConfirm] = useState(false)
  return (
    <div className="flex flex-wrap items-center justify-between gap-3 rounded-xl border border-gray-200 bg-white px-4 py-3">
      <div className="min-w-0">
        <p className="text-sm font-semibold text-gray-900 truncate">📄 {resume.filename}</p>
        <p className="text-xs text-gray-500">Uploaded {formatDate(resume.uploaded_at)}</p>
      </div>
      {confirm ? (
        <span className="flex items-center gap-2 text-sm">
          Delete resume and matches?
          <button
            type="button"
            onClick={() => del.mutate(undefined, { onSuccess: () => setConfirm(false) })}
            disabled={del.isPending}
            className="px-3 py-1 rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
          >
            {del.isPending ? 'Deleting…' : 'Delete'}
          </button>
          <button type="button" onClick={() => setConfirm(false)} className="px-3 py-1 rounded-lg border border-gray-300">
            Cancel
          </button>
        </span>
      ) : (
        <button type="button" onClick={() => setConfirm(true)} className="text-sm text-red-600 hover:text-red-800">
          Delete
        </button>
      )}
    </div>
  )
}

// ── Step 2: insights ──────────────────────────────────────────────────────────

function Chips({ items, tone }: { items: string[]; tone: 'green' | 'amber' | 'blue' }) {
  const cls = {
    green: 'bg-green-50 text-green-800 border-green-200',
    amber: 'bg-amber-50 text-amber-900 border-amber-200',
    blue: 'bg-blue-50 text-blue-800 border-blue-200',
  }[tone]
  return (
    <ul className="flex flex-wrap gap-2" role="list">
      {items.map((s) => (
        <li key={s} className={`px-2.5 py-1 text-sm rounded-full border ${cls}`}>{s}</li>
      ))}
    </ul>
  )
}

function ReviewList({ title, items, icon }: { title: string; items: string[]; icon: string }) {
  if (items.length === 0) return null
  return (
    <div>
      <h4 className="font-semibold text-gray-900">{icon} {title}</h4>
      <ul className="mt-1 list-disc pl-5 space-y-1 text-sm text-gray-700">
        {items.map((t) => <li key={t}>{t}</li>)}
      </ul>
    </div>
  )
}

function AiReview({ review }: { review: AIInsights }) {
  return (
    <div className="space-y-4">
      {review.summary && <p className="text-gray-800">{review.summary}</p>}
      <div className="grid gap-4 md:grid-cols-2">
        <ReviewList title="What you're good at" items={review.strengths} icon="💪" />
        <ReviewList title="What to fix" items={review.improvements} icon="🛠️" />
        <ReviewList title="How to tailor it" items={review.tailoring_tips} icon="🎯" />
        {review.roles_to_search.length > 0 && (
          <div>
            <h4 className="font-semibold text-gray-900">🔎 Roles to search for</h4>
            <ul className="mt-2 flex flex-wrap gap-2" role="list">
              {review.roles_to_search.map((r) => (
                <li key={r}>
                  <Link
                    to={`/?q=${encodeURIComponent(r)}`}
                    className="inline-block px-2.5 py-1 text-sm rounded-full border border-blue-200 bg-blue-50 text-blue-800 hover:bg-blue-100"
                  >
                    {r}
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      {review.keywords_to_add.length > 0 && (
        <div>
          <h4 className="font-semibold text-gray-900">🏷️ Keywords to add — only if they're true for you</h4>
          <div className="mt-2"><Chips items={review.keywords_to_add} tone="blue" /></div>
        </div>
      )}
    </div>
  )
}

function InsightsSection() {
  const { data, isLoading } = useInsights(true)
  const generate = useGenerateInsights()
  const canUseAi = useCanUseAi()
  const aiKey = useAiKey()

  if (isLoading || !data) {
    return <div className="h-40 rounded-2xl bg-white border border-gray-200 animate-pulse" />
  }

  return (
    <section aria-labelledby="insights-heading" className="space-y-4">
      <h2 id="insights-heading" className="text-xl font-bold text-gray-900">2. What your resume says</h2>

      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-2xl border border-gray-200 bg-white p-5">
          <h3 className="font-semibold text-gray-900">✅ Skills employers can see</h3>
          <p className="text-sm text-gray-500 mb-3">Found on your resume and asked for in real postings.</p>
          {data.skills_found.length > 0 ? (
            <Chips items={data.skills_found} tone="green" />
          ) : (
            <p className="text-sm text-gray-600">
              We couldn't spot any listed skills. Add a clear <strong>Skills</strong> section — e.g.
              "Python, SQL, React" — so recruiters and filters can find them.
            </p>
          )}
        </div>
        <div className="rounded-2xl border border-gray-200 bg-white p-5">
          <h3 className="font-semibold text-gray-900">📈 In demand, but not on your resume</h3>
          <p className="text-sm text-gray-500 mb-3">
            The most-requested skills in open postings. Add the ones you really have, or pick one to learn next.
          </p>
          {data.in_demand_missing.length > 0 ? (
            <ul className="space-y-1.5" role="list">
              {data.in_demand_missing.map((m) => (
                <li key={m.skill} className="flex items-center justify-between text-sm">
                  <span className="font-medium text-amber-900">{m.skill}</span>
                  <span className="text-gray-500">{m.postings} job{m.postings === 1 ? '' : 's'}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-600">Nice — you already cover the most-requested skills.</p>
          )}
        </div>
      </div>

      <div className="rounded-2xl border border-indigo-200 bg-gradient-to-br from-indigo-50 to-white p-5 space-y-4">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="font-semibold text-gray-900">🤖 AI resume review</h3>
            <p className="text-sm text-gray-600">
              Strengths, fixes, tailoring tips, and roles to search — written for your resume.
            </p>
          </div>
          {canUseAi ? (
            <button
              type="button"
              onClick={() => generate.mutate()}
              disabled={generate.isPending}
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700 disabled:opacity-60"
            >
              {generate.isPending ? 'Reviewing… (about 20 s)' : data.ai ? 'Refresh review' : 'Get my AI review'}
            </button>
          ) : (
            <Link
              to="/ai-key"
              className="px-4 py-2 rounded-lg bg-indigo-600 text-white text-sm font-semibold hover:bg-indigo-700"
            >
              Add a free AI key
            </Link>
          )}
        </div>
        {!canUseAi && !data.ai && (
          <p className="text-sm text-gray-600">
            Uses your own Claude, ChatGPT, or Gemini key — Gemini's free tier works, and setup takes about two minutes.
          </p>
        )}
        {aiKey && !data.ai && !generate.isPending && (
          <p className="text-xs text-gray-500">Runs on your {providerName(aiKey.provider)} key ({aiKey.model}).</p>
        )}
        {generate.isError && <p role="alert" className="text-sm text-red-600">{generate.error.message}</p>}
        {data.ai && <AiReview review={data.ai} />}
      </div>
    </section>
  )
}

// ── Step 3: jobs to apply for ─────────────────────────────────────────────────

function scoreClass(score: number): string {
  if (score >= 70) return 'bg-green-100 text-green-800 border-green-200'
  if (score >= 40) return 'bg-yellow-100 text-yellow-800 border-yellow-200'
  return 'bg-gray-100 text-gray-700 border-gray-200'
}

function MatchCard({ match }: { match: MatchResultOut }) {
  return (
    <article className="rounded-2xl border border-gray-200 bg-white p-5 shadow-sm space-y-3">
      <div className="flex items-start gap-3">
        <span
          className={`shrink-0 inline-flex items-center justify-center w-12 h-12 rounded-xl border text-lg font-bold ${scoreClass(match.score)}`}
          aria-label={`Match score ${match.score} out of 100`}
        >
          {match.score}
        </span>
        <div className="min-w-0 flex-1">
          <Link to={`/postings/${match.posting_id}`} className="text-base font-semibold text-gray-900 hover:text-blue-700">
            {match.title}
          </Link>
          <p className="text-sm text-gray-600">
            {match.company} · {formatLocation(match.city, match.province)}
            {match.term && match.term !== 'Open' ? ` · ${match.term}` : ''}
            {match.deadline ? ` · apply by ${formatDate(match.deadline)}` : ''}
          </p>
        </div>
      </div>
      <p className="text-sm text-gray-700">{match.reason}</p>
      <ConversationPanel postingId={match.posting_id} postingTitle={match.title} company={match.company} />
    </article>
  )
}

function MatchesSection({ items }: { items: MatchResultOut[] }) {
  const canUseAi = useCanUseAi()
  const rematch = useRematch()

  return (
    <section aria-labelledby="matches-heading" className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h2 id="matches-heading" className="text-xl font-bold text-gray-900">3. Jobs to apply for</h2>
          <p className="text-sm text-gray-500">
            Your best fits among open postings. Open one to apply on the company's site.
          </p>
        </div>
        {canUseAi && items.length > 0 && (
          <button
            type="button"
            onClick={() => rematch.mutate()}
            disabled={rematch.isPending}
            className="text-sm px-3 py-1.5 rounded-lg border border-indigo-300 text-indigo-700 hover:bg-indigo-50 disabled:opacity-60"
          >
            {rematch.isPending ? 'Re-ranking… (about 30 s)' : '✨ Re-rank with my AI'}
          </button>
        )}
      </div>
      {rematch.isError && <p role="alert" className="text-sm text-red-600">{rematch.error.message}</p>}

      {items.length === 0 ? (
        <div className="rounded-2xl border border-gray-200 bg-white p-6 text-sm text-gray-600">
          No open postings match yet. New jobs are pulled in every few hours —{' '}
          <Link to="/" className="text-blue-700 hover:underline">browse all jobs</Link> in the meantime.
        </div>
      ) : (
        <ol className="space-y-4" aria-label="Matched jobs">
          {items.map((m) => <li key={m.posting_id}><MatchCard match={m} /></li>)}
        </ol>
      )}
    </section>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ResumePage() {
  const { data: me, isLoading: meLoading } = useMe()
  const { data, isLoading } = useMatches(Boolean(me))
  const resume = data?.resume ?? null

  return (
    <div className="max-w-4xl mx-auto px-4 py-8 space-y-8">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">Your resume, decoded</h1>
        <p className="mt-2 text-gray-600 max-w-2xl">
          Upload once. See what you're good at, what employers want that you're missing, how to tailor
          it — and which real jobs to apply for.
        </p>
      </header>

      <section aria-labelledby="upload-heading" className="space-y-3">
        <h2 id="upload-heading" className="text-xl font-bold text-gray-900">1. Your resume</h2>
        {meLoading || (me && isLoading) ? (
          <div className="h-32 rounded-2xl bg-white border border-gray-200 animate-pulse" />
        ) : (
          <>
            {resume && <StoredResume resume={resume} />}
            <ResumeDropzone compact={Boolean(resume)} />
          </>
        )}
      </section>

      {resume && (
        <>
          <InsightsSection />
          <MatchesSection items={data?.items ?? []} />
        </>
      )}
    </div>
  )
}
