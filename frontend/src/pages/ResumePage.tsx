/**
 * ResumePage: /resume, the heart of CoopRadar.
 *
 *   1. About you and what you're looking for: program, degree, graduation year, co-op or
 *      new grad, term, countries, then job types, keywords, location and work mode.
 *      Program, degree and graduation year are read from the resume when left blank.
 *   2. Your resume (no account needed: a private temporary account is created)
 *   3. Results, in two tabs:
 *      - Matching jobs: ranked for this resume within the preferences, each with why it fits
 *        (role, the program and graduation year the posting names, term, skills), the skills
 *        it wants that the resume shows or lacks, plus tailor / cover letter tools
 *      - Resume feedback: skills found, in-demand skills missing (free) and an AI review
 *        (visitor's own key)
 *
 * Before the first upload, preferences are kept in this browser and sent with the file.
 * Afterwards they're saved on the resume, and changing them re-matches for free.
 */

import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router-dom'
import { useQueryClient } from '@tanstack/react-query'
import { providerName, useAiKey } from '../api/aiKey'
import { guestLogin, useMe } from '../api/auth'
import { ApiError } from '../api/client'
import { usePublicConfig } from '../api/meta'
import { useFilterMeta, type CategoryKey, type CountryCode, type WorkMode } from '../api/postings'
import { useSavePosting } from '../api/saved'
import {
  DEFAULT_PREFERENCES,
  useDeleteResume,
  useGenerateInsights,
  useInsights,
  useMatches,
  useRematch,
  useUpdatePreferences,
  useUploadResume,
  type AIInsights,
  type Degree,
  type DetectedEducation,
  type JobPreferences,
  type MatchResultOut,
  type ResumeOut,
} from '../api/resume'
import AuthModal from '../components/AuthModal'
import ConversationPanel from '../components/ConversationPanel'
import {
  ArrowRightIcon, CheckIcon, ExternalIcon, FileIcon, PinIcon, TrendIcon, UploadIcon,
} from '../components/Icons'
import { gradYears } from '../components/filters'
import { CompanyInitial } from '../components/PostingCard'
import { formatDate, formatLocation, isProvince, provinceName, workModeLabel } from '../utils/format'

const MAX_SIZE_BYTES = 5 * 1024 * 1024
const PREFS_KEY = 'coopradar.preferences'
const WORK_MODES: WorkMode[] = ['onsite', 'hybrid', 'remote']
const LEVELS: { value: JobPreferences['level']; label: string }[] = [
  { value: 'students', label: 'Co-op or internship' },
  { value: 'entry', label: 'Co-op, internship or entry-level' },
  { value: 'all', label: 'Any level' },
]
const DEGREES: { value: Degree; label: string }[] = [
  { value: 'diploma', label: 'College diploma' },
  { value: 'bachelors', label: "Bachelor's" },
  { value: 'masters', label: "Master's" },
  { value: 'phd', label: 'PhD' },
]
const COUNTRIES: { value: CountryCode; label: string }[] = [
  { value: 'CA', label: 'Canada' },
  { value: 'US', label: 'United States' },
]

/** The next six co-op terms (Winter = Jan, Summer = May, Fall = Sep). */
function upcomingTerms(now: Date = new Date()): string[] {
  const seasons = [['Winter', 0], ['Summer', 4], ['Fall', 8]] as const
  const terms: string[] = []
  for (let year = now.getFullYear(); terms.length < 6; year++) {
    for (const [name, month] of seasons) {
      if (new Date(year, month, 1) > now && terms.length < 6) terms.push(`${name} ${year}`)
    }
  }
  return terms
}

function useCanUseAi(): boolean {
  const aiKey = useAiKey()
  const { data: config } = usePublicConfig()
  return Boolean(aiKey) || Boolean(config?.server_ai_enabled)
}

/** Preferences picked before uploading live in this browser (storage can be unavailable). */
function loadLocalPrefs(): JobPreferences {
  try {
    const raw = localStorage.getItem(PREFS_KEY)
    if (raw) return { ...DEFAULT_PREFERENCES, ...(JSON.parse(raw) as Partial<JobPreferences>) }
  } catch {
    // private mode or blocked storage: start fresh
  }
  return DEFAULT_PREFERENCES
}

function saveLocalPrefs(prefs: JobPreferences) {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs))
  } catch {
    // not critical
  }
}

const samePrefs = (a: JobPreferences, b: JobPreferences) => JSON.stringify(a) === JSON.stringify(b)

function StepCard({
  step, title, subtitle, done = false, children,
}: { step: number; title: string; subtitle?: string; done?: boolean; children: React.ReactNode }) {
  return (
    <section aria-labelledby={`step-${step}`} className="rounded-xl border border-gray-200 bg-white">
      <div className="flex items-start gap-3 border-b border-gray-100 px-5 py-4 sm:px-6">
        <span
          className={`mt-0.5 flex h-7 w-7 shrink-0 items-center justify-center rounded-full text-sm font-semibold ${
            done ? 'bg-blue-700 text-white' : 'bg-gray-100 text-gray-700'
          }`}
          aria-hidden="true"
        >
          {done ? <CheckIcon className="h-4 w-4" /> : step}
        </span>
        <div>
          <h2 id={`step-${step}`} className="text-lg font-semibold text-gray-900">{title}</h2>
          {subtitle && <p className="text-sm text-gray-600">{subtitle}</p>}
        </div>
      </div>
      <div className="px-5 py-5 sm:px-6">{children}</div>
    </section>
  )
}

// ── Step 1: what you're looking for ───────────────────────────────────────────

function Toggle({
  on, onClick, children, count,
}: { on: boolean; onClick: () => void; children: React.ReactNode; count?: number }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={`inline-flex items-center gap-1.5 rounded-full border px-3 py-1.5 text-sm transition-colors ${
        on
          ? 'border-blue-700 bg-blue-700 text-white'
          : 'border-gray-300 bg-white text-gray-800 hover:border-gray-500'
      }`}
    >
      {on && <CheckIcon className="h-3.5 w-3.5" />}
      {children}
      {count !== undefined && (
        <span className={`text-xs tabular-nums ${on ? 'text-blue-100' : 'text-gray-500'}`}>{count}</span>
      )}
    </button>
  )
}

const fieldClass =
  'mt-1.5 w-full rounded-md border border-gray-400 bg-white px-3 py-2 text-sm focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600'

function AboutYou({
  prefs, onChange, education,
}: {
  prefs: JobPreferences
  onChange: (p: JobPreferences) => void
  education: DetectedEducation | null
}) {
  const { data: meta } = useFilterMeta()
  const programs = meta?.programs ?? []
  const found = education && (education.program || education.degree || education.grad_year) ? education : null
  const fromResume = (text: string) => `From your resume: ${text}`
  const degreeLabel = DEGREES.find((d) => d.value === education?.degree)?.label

  return (
    <div className="space-y-5">
      {found && (
        <p className="rounded-md bg-blue-50 px-3 py-2 text-sm text-blue-900">
          We read your resume:{' '}
          {[found.program_label, degreeLabel, found.grad_year ? `graduating ${found.grad_year}` : '']
            .filter(Boolean).join(', ')}.
          {' '}Change anything that's wrong.
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="sm:col-span-3 md:col-span-1">
          <label htmlFor="pref-program" className="text-sm font-semibold text-gray-900">Program or major</label>
          <select
            id="pref-program"
            value={prefs.program}
            onChange={(e) => onChange({ ...prefs, program: e.target.value as JobPreferences['program'] })}
            className={fieldClass}
          >
            <option value="">{found?.program_label ? fromResume(found.program_label) : 'Read it from my resume'}</option>
            {programs.map((p) => <option key={p.key} value={p.key}>{p.label}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="pref-degree" className="text-sm font-semibold text-gray-900">Degree</label>
          <select
            id="pref-degree"
            value={prefs.degree}
            onChange={(e) => onChange({ ...prefs, degree: e.target.value as Degree })}
            className={fieldClass}
          >
            <option value="">{degreeLabel ? fromResume(degreeLabel) : 'Read it from my resume'}</option>
            {DEGREES.map((d) => <option key={d.value} value={d.value}>{d.label}</option>)}
          </select>
        </div>
        <div>
          <label htmlFor="pref-grad" className="text-sm font-semibold text-gray-900">Graduating in</label>
          <select
            id="pref-grad"
            value={prefs.grad_year ?? ''}
            onChange={(e) => onChange({ ...prefs, grad_year: e.target.value ? Number(e.target.value) : null })}
            className={fieldClass}
          >
            <option value="">{found?.grad_year ? fromResume(String(found.grad_year)) : 'Read it from my resume'}</option>
            {gradYears().map((y) => <option key={y} value={y}>{y}</option>)}
          </select>
        </div>
      </div>

      <fieldset>
        <legend className="text-sm font-semibold text-gray-900">Looking for</legend>
        <div className="mt-1.5 inline-flex flex-wrap rounded-md border border-gray-400 bg-gray-50 p-1">
          {LEVELS.map((l) => (
            <label
              key={l.value}
              className={`cursor-pointer rounded px-3 py-1.5 text-sm ${
                prefs.level === l.value ? 'bg-white font-semibold text-gray-900 shadow-sm ring-1 ring-gray-300' : 'text-gray-700 hover:text-gray-900'
              }`}
            >
              <input
                type="radio"
                name="pref-level"
                className="sr-only"
                checked={prefs.level === l.value}
                onChange={() => onChange({ ...prefs, level: l.value })}
              />
              {l.label}
            </label>
          ))}
        </div>
      </fieldset>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <label htmlFor="pref-term" className="text-sm font-semibold text-gray-900">
            Co-op term <span className="font-normal text-gray-500">(optional)</span>
          </label>
          <select
            id="pref-term"
            value={prefs.term}
            onChange={(e) => onChange({ ...prefs, term: e.target.value })}
            className={fieldClass}
          >
            <option value="">Any term</option>
            {upcomingTerms().map((t) => <option key={t} value={t}>{t}</option>)}
          </select>
          <p className="mt-1 text-xs text-gray-500">Jobs for this term are ranked higher.</p>
        </div>
        <fieldset>
          <legend className="text-sm font-semibold text-gray-900">Countries</legend>
          <div className="mt-2.5 flex flex-wrap gap-4">
            {COUNTRIES.map((c) => (
              <label key={c.value} className="flex cursor-pointer items-center gap-2 text-sm text-gray-800">
                <input
                  type="checkbox"
                  className="h-4 w-4 rounded border-gray-400 text-blue-600 focus:ring-blue-600"
                  checked={prefs.countries.includes(c.value)}
                  onChange={(e) => {
                    const next = e.target.checked
                      ? [...prefs.countries, c.value]
                      : prefs.countries.filter((x) => x !== c.value)
                    onChange({ ...prefs, countries: next.length ? next : ['CA'], province: '', city: '' })
                  }}
                />
                {c.label}
              </label>
            ))}
          </div>
          <p className="mt-1.5 text-xs text-gray-500">US jobs here are internships and new grad roles.</p>
        </fieldset>
      </div>
    </div>
  )
}

function PreferencesForm({
  prefs, onChange, hasResume, saved,
}: {
  prefs: JobPreferences
  onChange: (p: JobPreferences) => void
  hasResume: boolean
  /** What's saved on the server (null before the first upload) */
  saved: JobPreferences | null
}) {
  const { data: meta } = useFilterMeta()
  const update = useUpdatePreferences()
  const categories = meta?.categories ?? []
  const dirty = hasResume && !samePrefs(prefs, { ...DEFAULT_PREFERENCES, ...(saved ?? {}) })
  const regions = (meta?.provinces ?? []).filter((p) =>
    prefs.countries.includes(isProvince(p) ? 'CA' : 'US'),
  )

  const toggle = <T,>(list: T[], value: T) =>
    list.includes(value) ? list.filter((v) => v !== value) : [...list, value]

  return (
    <div className="space-y-6">
      <fieldset>
        <legend className="text-sm font-semibold text-gray-900">Job type</legend>
        <p className="mb-2.5 text-sm text-gray-500">
          Pick any that interest you. Leave empty and we'll use the usual job types for your program.
        </p>
        <div className="flex flex-wrap gap-2">
          {categories.map((c) => (
            <Toggle
              key={c.key}
              on={prefs.categories.includes(c.key)}
              onClick={() => onChange({ ...prefs, categories: toggle<CategoryKey>(prefs.categories, c.key) })}
              count={c.count}
            >
              {c.label}
            </Toggle>
          ))}
          {categories.length === 0 && <p className="text-sm text-gray-500">Loading job types...</p>}
        </div>
      </fieldset>

      <div>
        <label htmlFor="pref-keywords" className="text-sm font-semibold text-gray-900">
          Job title or keywords <span className="font-normal text-gray-500">(optional)</span>
        </label>
        <input
          id="pref-keywords"
          type="text"
          maxLength={100}
          value={prefs.keywords}
          onChange={(e) => onChange({ ...prefs, keywords: e.target.value })}
          placeholder="For example: data analyst, frontend, marketing"
          className={`${fieldClass} placeholder-gray-500`}
        />
        <p className="mt-1 text-xs text-gray-500">Jobs that mention these are ranked higher.</p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        <div>
          <label htmlFor="pref-province" className="text-sm font-semibold text-gray-900">Where</label>
          <select
            id="pref-province"
            value={prefs.province}
            onChange={(e) => onChange({ ...prefs, province: e.target.value, city: '' })}
            className={fieldClass}
          >
            <option value="">Anywhere</option>
            {regions.map((p) => <option key={p} value={p}>{provinceName(p)}</option>)}
          </select>
          <p className="mt-1 text-xs text-gray-500">Remote jobs are always included.</p>
        </div>

        <fieldset>
          <legend className="text-sm font-semibold text-gray-900">Work mode</legend>
          <div className="mt-1.5 flex flex-wrap gap-2">
            {WORK_MODES.map((m) => (
              <Toggle
                key={m}
                on={prefs.work_modes.includes(m)}
                onClick={() => onChange({ ...prefs, work_modes: toggle<WorkMode>(prefs.work_modes, m) })}
              >
                {workModeLabel(m)}
              </Toggle>
            ))}
          </div>
        </fieldset>
      </div>

      {hasResume && (
        <div className="flex flex-wrap items-center gap-3 border-t border-gray-100 pt-5">
          <button
            type="button"
            disabled={!dirty || update.isPending}
            onClick={() => update.mutate(prefs)}
            className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:cursor-not-allowed disabled:opacity-50"
          >
            {update.isPending ? 'Updating matches...' : 'Update my matches'}
          </button>
          {dirty && !update.isPending && <span className="text-sm text-gray-600">You changed your preferences.</span>}
          {update.isSuccess && !dirty && <span className="text-sm text-blue-800">Matches updated.</span>}
          {update.isError && <span role="alert" className="text-sm text-red-600">{update.error.message}</span>}
        </div>
      )}
    </div>
  )
}

// ── Step 2: upload ────────────────────────────────────────────────────────────

function ResumeDropzone({ compact, prefs }: { compact: boolean; prefs: JobPreferences }) {
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
    upload.mutate({ file, preferences: prefs }, {
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
        className={`flex cursor-pointer flex-col items-center rounded-lg border-2 border-dashed text-center transition-colors ${
          compact ? 'px-4 py-4' : 'px-6 py-10'
        } ${dragging ? 'border-blue-600 bg-blue-50' : 'border-gray-300 bg-gray-50 hover:border-blue-500 hover:bg-blue-50/50'}`}
      >
        {busy ? (
          <span className="font-medium text-blue-800 animate-pulse">
            Reading your resume and finding matching jobs...
          </span>
        ) : compact ? (
          <span className="flex items-center gap-2 text-sm text-gray-700">
            <UploadIcon className="h-4 w-4 text-blue-700" />
            <span><span className="font-semibold text-blue-800">Drop your resume here</span> to replace it, or browse</span>
          </span>
        ) : (
          <>
            <span className="flex h-12 w-12 items-center justify-center rounded-full bg-white text-blue-700 ring-1 ring-gray-200">
              <UploadIcon className="h-6 w-6" />
            </span>
            <span className="mt-3 block text-base font-semibold text-gray-900">
              Drop your resume here, or <span className="text-blue-700 underline underline-offset-2">browse</span>
            </span>
            <span className="mt-1 block text-sm text-gray-500">PDF or Word (.docx), up to 5 MB. No sign-up needed.</span>
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
        <p className="mt-3 text-xs text-gray-500">
          Your resume stays private in your account and only goes to an AI if you add your own key. Delete it any time.
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
    <div className="mb-3 flex flex-wrap items-center justify-between gap-3 rounded-lg border border-gray-200 px-4 py-3">
      <div className="flex min-w-0 items-center gap-3">
        <FileIcon className="h-5 w-5 shrink-0 text-blue-700" />
        <div className="min-w-0">
          <p className="truncate text-sm font-semibold text-gray-900">{resume.filename}</p>
          <p className="text-xs text-gray-500">Uploaded {formatDate(resume.uploaded_at)}</p>
        </div>
      </div>
      {confirm ? (
        <span className="flex items-center gap-2 text-sm">
          Delete your resume and matches?
          <button
            type="button"
            onClick={() => del.mutate(undefined, { onSuccess: () => setConfirm(false) })}
            disabled={del.isPending}
            className="rounded-md bg-red-600 px-3 py-1 text-white hover:bg-red-700 disabled:opacity-50"
          >
            {del.isPending ? 'Deleting...' : 'Delete'}
          </button>
          <button type="button" onClick={() => setConfirm(false)} className="rounded-md border border-gray-300 px-3 py-1">
            Cancel
          </button>
        </span>
      ) : (
        <button type="button" onClick={() => setConfirm(true)} className="text-sm text-gray-500 hover:text-red-700">
          Delete
        </button>
      )}
    </div>
  )
}

// ── Results: matching jobs ────────────────────────────────────────────────────

function scoreTone(score: number): { ring: string; label: string } {
  if (score >= 70) return { ring: 'bg-blue-700 text-white', label: 'Strong match' }
  if (score >= 40) return { ring: 'bg-blue-100 text-blue-900', label: 'Good match' }
  return { ring: 'bg-gray-100 text-gray-700', label: 'Possible match' }
}

function SkillList({ title, items, have }: { title: string; items: string[]; have: boolean }) {
  if (items.length === 0) return null
  return (
    <div>
      <p className="mb-1.5 text-xs font-medium text-gray-500">{title}</p>
      <ul className="flex flex-wrap gap-1.5" role="list">
        {items.map((s) => (
          <li
            key={s}
            className={`inline-flex items-center gap-1 rounded px-2 py-0.5 text-sm ${
              have ? 'bg-blue-50 text-blue-900' : 'border border-dashed border-gray-300 text-gray-700'
            }`}
          >
            {have && <CheckIcon className="h-3.5 w-3.5" />}
            {s}
          </li>
        ))}
      </ul>
    </div>
  )
}

function MatchCard({ match, rank }: { match: MatchResultOut; rank: number }) {
  const tone = scoreTone(match.score)
  const hasSkills = match.matched_skills.length > 0 || match.missing_skills.length > 0
  return (
    <article className="rounded-lg border border-gray-200 bg-white p-5" aria-label={`${match.title} at ${match.company}`}>
      <div className="flex items-start gap-4">
        <CompanyInitial name={match.company} />
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-2">
            <div className="min-w-0">
              <p className="text-xs text-gray-500">#{rank}</p>
              <Link to={`/postings/${match.posting_id}`} className="font-semibold leading-snug text-gray-900 hover:text-blue-800">
                {match.title}
              </Link>
              <p className="mt-0.5 text-sm text-gray-600">
                {match.company}
                <span className="mx-1.5 text-gray-300" aria-hidden="true">|</span>
                <PinIcon className="mr-0.5 inline h-3.5 w-3.5 -translate-y-px text-gray-400" />
                {formatLocation(match.city, match.province, match.country)}
                {match.work_mode ? ` · ${workModeLabel(match.work_mode)}` : ''}
                {match.term && match.term !== 'Open' ? ` · ${match.term}` : ''}
              </p>
            </div>
            <div className="flex items-center gap-2" aria-label={`Match score ${match.score} out of 100`}>
              <span className={`flex h-11 w-11 items-center justify-center rounded-full text-base font-bold tabular-nums ${tone.ring}`}>
                {match.score}
              </span>
              <span className="text-xs leading-tight text-gray-600">{tone.label}</span>
            </div>
          </div>

          {/* The free ranking's reason only repeats the skill lists below, so show AI reasons only */}
          {!(hasSkills && /^(You have|None of its listed skills)/.test(match.reason)) && (
            <p className="mt-3 text-sm text-gray-700">{match.reason}</p>
          )}

          {match.fit_notes.length > 0 && (
            <div className="mt-3">
              <p className="mb-1.5 text-xs font-medium text-gray-500">Why it fits</p>
              <ul className="grid gap-x-4 gap-y-1 text-sm text-gray-800 sm:grid-cols-2" role="list">
                {match.fit_notes.map((n) => (
                  <li key={n} className="flex items-start gap-1.5">
                    <CheckIcon className="mt-0.5 h-4 w-4 shrink-0 text-green-700" />
                    {n}
                  </li>
                ))}
              </ul>
            </div>
          )}

          {hasSkills && (
            <div className="mt-3 grid gap-3 sm:grid-cols-2">
              <SkillList title="On your resume" items={match.matched_skills} have />
              <SkillList title="Worth adding, if you have it" items={match.missing_skills} have={false} />
            </div>
          )}

          <div className="mt-4 border-t border-gray-100 pt-4 space-y-3">
            <SaveAndApply postingId={match.posting_id} deadline={match.deadline} />
            <ConversationPanel postingId={match.posting_id} postingTitle={match.title} company={match.company} />
          </div>
        </div>
      </div>
    </article>
  )
}

/** Open the job to apply, or save it to the tracker (saving twice is harmless on the server). */
function SaveAndApply({ postingId, deadline }: { postingId: string; deadline: string }) {
  const save = useSavePosting()
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
      <Link
        to={`/postings/${postingId}`}
        className="inline-flex items-center gap-1.5 rounded-lg bg-blue-700 px-3 py-1.5 font-medium text-white hover:bg-blue-800"
      >
        View job and apply <ExternalIcon className="h-3.5 w-3.5" />
      </Link>
      {save.isSuccess ? (
        <Link to="/saved" className="inline-flex items-center gap-1 font-medium text-blue-800 hover:underline">
          <CheckIcon className="h-4 w-4" /> Saved to tracker
        </Link>
      ) : (
        <button
          type="button"
          onClick={() => save.mutate(postingId)}
          disabled={save.isPending}
          className="rounded-lg border border-gray-300 px-3 py-1.5 text-gray-700 hover:bg-gray-50 disabled:opacity-50"
        >
          {save.isPending ? 'Saving...' : 'Save to tracker'}
        </button>
      )}
      {deadline && <span className="text-gray-500">Apply by {formatDate(deadline)}</span>}
    </div>
  )
}

function MatchesTab({ items, prefs }: { items: MatchResultOut[]; prefs: JobPreferences | null }) {
  const canUseAi = useCanUseAi()
  const rematch = useRematch()
  const narrowed = prefs && !samePrefs(prefs, DEFAULT_PREFERENCES)

  return (
    <div className="space-y-4">
      <div className="flex flex-wrap items-end justify-between gap-3">
        <p className="text-sm text-gray-600">
          {items.length > 0
            ? 'Best fits first. Scores weigh your skills, your program and graduation year, and the term you want.'
            : null}
        </p>
        {canUseAi && items.length > 0 && (
          <button
            type="button"
            onClick={() => rematch.mutate()}
            disabled={rematch.isPending}
            className="rounded-lg border border-gray-300 bg-white px-3 py-1.5 text-sm text-gray-800 hover:bg-gray-50 disabled:opacity-60"
          >
            {rematch.isPending ? 'Re-ranking (about 30 seconds)...' : 'Re-rank with my AI'}
          </button>
        )}
      </div>
      {rematch.isError && <p role="alert" className="text-sm text-red-600">{rematch.error.message}</p>}

      {items.length === 0 ? (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-8 text-center">
          <p className="font-medium text-gray-900">No open jobs fit yet</p>
          <p className="mt-1 text-sm text-gray-600">
            {narrowed
              ? 'Try more job types, "Anywhere", adding the United States, or "Co-op, internship or entry-level" above.'
              : 'New jobs are imported every few hours.'}{' '}
            You can also <Link to="/" className="font-medium text-blue-700 hover:underline">browse all jobs</Link>.
          </p>
        </div>
      ) : (
        <ol className="space-y-4" aria-label="Matched jobs">
          {items.map((m, i) => <li key={m.posting_id}><MatchCard match={m} rank={i + 1} /></li>)}
        </ol>
      )}
    </div>
  )
}

// ── Results: resume feedback ──────────────────────────────────────────────────

function Chips({ items }: { items: string[] }) {
  return (
    <ul className="flex flex-wrap gap-1.5" role="list">
      {items.map((s) => (
        <li key={s} className="inline-flex items-center gap-1 rounded bg-blue-50 px-2 py-0.5 text-sm text-blue-900">
          <CheckIcon className="h-3.5 w-3.5" />{s}
        </li>
      ))}
    </ul>
  )
}

function ReviewList({ title, items }: { title: string; items: string[] }) {
  if (items.length === 0) return null
  return (
    <div>
      <h4 className="font-semibold text-gray-900">{title}</h4>
      <ul className="mt-1.5 list-disc space-y-1 pl-5 text-sm text-gray-700">
        {items.map((t) => <li key={t}>{t}</li>)}
      </ul>
    </div>
  )
}

function AiReview({ review }: { review: AIInsights }) {
  return (
    <div className="space-y-5">
      {review.summary && <p className="text-gray-800">{review.summary}</p>}
      <div className="grid gap-5 md:grid-cols-2">
        <ReviewList title="What you're good at" items={review.strengths} />
        <ReviewList title="What to fix" items={review.improvements} />
        <ReviewList title="How to tailor it" items={review.tailoring_tips} />
        {review.roles_to_search.length > 0 && (
          <div>
            <h4 className="font-semibold text-gray-900">Roles to search for</h4>
            <ul className="mt-2 flex flex-wrap gap-2" role="list">
              {review.roles_to_search.map((r) => (
                <li key={r}>
                  <Link
                    to={`/?q=${encodeURIComponent(r)}`}
                    className="inline-flex items-center gap-1 rounded-full border border-gray-300 px-3 py-1 text-sm text-gray-800 hover:border-blue-600 hover:text-blue-800"
                  >
                    {r} <ArrowRightIcon className="h-3.5 w-3.5" />
                  </Link>
                </li>
              ))}
            </ul>
          </div>
        )}
      </div>
      {review.keywords_to_add.length > 0 && (
        <div>
          <h4 className="font-semibold text-gray-900">Keywords to add, only if they're true for you</h4>
          <p className="mt-1 text-sm text-gray-700">{review.keywords_to_add.join(', ')}</p>
        </div>
      )}
    </div>
  )
}

function FeedbackTab() {
  const { data, isLoading } = useInsights(true)
  const generate = useGenerateInsights()
  const canUseAi = useCanUseAi()
  const aiKey = useAiKey()

  if (isLoading || !data) {
    return <div className="h-40 animate-pulse rounded-lg border border-gray-200 bg-white" />
  }

  return (
    <div className="space-y-4">
      <div className="grid gap-4 md:grid-cols-2">
        <div className="rounded-lg border border-gray-200 bg-white p-5">
          <h3 className="flex items-center gap-2 font-semibold text-gray-900">
            <CheckIcon className="h-5 w-5 text-blue-700" /> Skills employers can see
          </h3>
          <p className="mb-3 mt-0.5 text-sm text-gray-500">On your resume and asked for in real job postings.</p>
          {data.skills_found.length > 0 ? (
            <Chips items={data.skills_found} />
          ) : (
            <p className="text-sm text-gray-700">
              We couldn't find any listed skills. Add a clear <strong>Skills</strong> section, for example
              "Python, SQL, React", so recruiters and filters can find them.
            </p>
          )}
        </div>
        <div className="rounded-lg border border-gray-200 bg-white p-5">
          <h3 className="flex items-center gap-2 font-semibold text-gray-900">
            <TrendIcon className="h-5 w-5 text-blue-700" /> In demand, but not on your resume
          </h3>
          <p className="mb-3 mt-0.5 text-sm text-gray-500">
            The skills open jobs ask for most. Add the ones you have, or pick one to learn next.
          </p>
          {data.in_demand_missing.length > 0 ? (
            <ul className="divide-y divide-gray-100" role="list">
              {data.in_demand_missing.map((m) => (
                <li key={m.skill} className="flex items-center justify-between py-1.5 text-sm">
                  <span className="font-medium text-gray-900">{m.skill}</span>
                  <span className="tabular-nums text-gray-500">{m.postings} job{m.postings === 1 ? '' : 's'}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-700">You already list the most-requested skills.</p>
          )}
        </div>
      </div>

      <div className="space-y-4 rounded-lg border border-gray-200 bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="font-semibold text-gray-900">Full resume review</h3>
            <p className="text-sm text-gray-600">
              Strengths, what to fix, how to tailor it, and roles to search for, written for your resume.
            </p>
          </div>
          {canUseAi ? (
            <button
              type="button"
              onClick={() => generate.mutate()}
              disabled={generate.isPending}
              className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800 disabled:opacity-60"
            >
              {generate.isPending ? 'Reviewing (about 20 seconds)...' : data.ai ? 'Refresh review' : 'Review my resume'}
            </button>
          ) : (
            <Link to="/ai-key" className="rounded-lg bg-blue-700 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-800">
              Add a free AI key
            </Link>
          )}
        </div>
        {!canUseAi && !data.ai && (
          <p className="text-sm text-gray-600">
            This part uses your own Claude, ChatGPT or Gemini key. Gemini has a free tier, and setup takes about two minutes.
          </p>
        )}
        {aiKey && !data.ai && !generate.isPending && (
          <p className="text-xs text-gray-500">Runs on your {providerName(aiKey.provider)} key ({aiKey.model}).</p>
        )}
        {generate.isError && <p role="alert" className="text-sm text-red-600">{generate.error.message}</p>}
        {data.ai && <AiReview review={data.ai} />}
      </div>
    </div>
  )
}

// ── Page ──────────────────────────────────────────────────────────────────────

export default function ResumePage() {
  const { data: me, isLoading: meLoading } = useMe()
  const { data, isLoading } = useMatches(Boolean(me))
  const resume = data?.resume ?? null
  const savedPrefs = data?.preferences ?? null
  const education = data?.education ?? null
  const [prefs, setPrefs] = useState<JobPreferences>(loadLocalPrefs)
  const [tab, setTab] = useState<'jobs' | 'feedback'>('jobs')

  // Once a resume exists, the form starts from what's saved with it
  const resumeId = resume?.id
  useEffect(() => {
    if (resumeId && savedPrefs) setPrefs({ ...DEFAULT_PREFERENCES, ...savedPrefs })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [resumeId, JSON.stringify(savedPrefs)])

  function changePrefs(next: JobPreferences) {
    setPrefs(next)
    saveLocalPrefs(next)
  }

  const items = data?.items ?? []

  return (
    <div className="mx-auto max-w-4xl space-y-6 px-4 py-6 sm:py-8">
      <header>
        <h1 className="text-3xl font-bold tracking-tight text-gray-900">Find co-op jobs that fit you</h1>
        <p className="mt-2 max-w-2xl text-gray-600">
          Tell us about your studies and what you want, upload your resume, and see the jobs you're a
          good fit for: matched to your program, graduation year and skills, using what each job
          description asks for.
        </p>
      </header>

      <StepCard
        step={1}
        title="About you"
        subtitle="Leave these on 'Read it from my resume' and we'll find them for you."
        done={Boolean(resume)}
      >
        <AboutYou prefs={prefs} onChange={changePrefs} education={education} />
      </StepCard>

      <StepCard
        step={2}
        title="What kind of job?"
        subtitle="Matches only include jobs that fit these. You can change them any time."
        done={Boolean(resume)}
      >
        <PreferencesForm prefs={prefs} onChange={changePrefs} hasResume={Boolean(resume)} saved={savedPrefs} />
      </StepCard>

      <StepCard
        step={3}
        title="Your resume"
        subtitle={resume ? undefined : 'We read your skills and studies, and rank open jobs for you.'}
        done={Boolean(resume)}
      >
        {meLoading || (me && isLoading) ? (
          <div className="h-32 animate-pulse rounded-lg bg-gray-100" />
        ) : (
          <>
            {resume && <StoredResume resume={resume} />}
            <ResumeDropzone compact={Boolean(resume)} prefs={prefs} />
          </>
        )}
      </StepCard>

      {resume && (
        <section aria-label="Results" className="space-y-4">
          <div className="flex gap-1 border-b border-gray-200" role="tablist">
            <TabButton active={tab === 'jobs'} onClick={() => setTab('jobs')} id="jobs">
              Jobs that fit your resume <span className="ml-1 text-gray-500 tabular-nums">{items.length}</span>
            </TabButton>
            <TabButton active={tab === 'feedback'} onClick={() => setTab('feedback')} id="feedback">
              Resume feedback
            </TabButton>
          </div>
          <div role="tabpanel" aria-labelledby={`tab-${tab}`}>
            {tab === 'jobs' ? <MatchesTab items={items} prefs={savedPrefs} /> : <FeedbackTab />}
          </div>
        </section>
      )}
    </div>
  )
}

function TabButton({
  active, onClick, id, children,
}: { active: boolean; onClick: () => void; id: string; children: React.ReactNode }) {
  return (
    <button
      type="button"
      role="tab"
      id={`tab-${id}`}
      aria-selected={active}
      onClick={onClick}
      className={`-mb-px border-b-2 px-4 py-2.5 text-sm font-medium ${
        active ? 'border-blue-700 text-gray-900' : 'border-transparent text-gray-600 hover:text-gray-900'
      }`}
    >
      {children}
    </button>
  )
}
