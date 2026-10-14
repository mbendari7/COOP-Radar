/**
 * The resume page at /resume, the heart of CoopRadar. It reads like a form in three parts.
 *
 *   1. About you. Program, degree, grad year, co-op or new grad, term and countries.
 *      Program, degree and grad year get read from the resume when left blank
 *   2. What kind of job. Job types, keywords, place and work mode
 *   3. Your resume. No account needed since a private temporary account gets made
 *   Then the results in two tabs
 *      Matching jobs are ranked for this resume within the preferences, each with why it fits,
 *      the skills it wants that the resume shows or lacks, and the tailor and cover letter tools
 *      Resume feedback has the skills found and popular skills missing for free, plus an AI
 *      review on the visitor's own key
 *
 * Before the first upload the preferences stay in this browser and go up with the file.
 * After that they are saved on the resume and changing them matches again for free.
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
import ResumeFitPanel from '../components/ResumeFitPanel'
import {
  ArrowRightIcon, CheckIcon, ExternalIcon, FileIcon, PinIcon, TrendIcon, UploadIcon,
} from '../components/Icons'
import { gradYears } from '../components/filters'
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

/** The next six co-op terms. Winter starts in January, Summer in May and Fall in September. */
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

/** Preferences picked before uploading live in this browser. Storage might not be there. */
function loadLocalPrefs(): JobPreferences {
  try {
    const raw = localStorage.getItem(PREFS_KEY)
    if (raw) return { ...DEFAULT_PREFERENCES, ...(JSON.parse(raw) as Partial<JobPreferences>) }
  } catch {
    // private mode or blocked storage, so just start fresh
  }
  return DEFAULT_PREFERENCES
}

function saveLocalPrefs(prefs: JobPreferences) {
  try {
    localStorage.setItem(PREFS_KEY, JSON.stringify(prefs))
  } catch {
    // not a big deal if this fails
  }
}

const samePrefs = (a: JobPreferences, b: JobPreferences) => JSON.stringify(a) === JSON.stringify(b)

function StepCard({
  step, title, subtitle, done = false, children,
}: { step: number; title: string; subtitle?: string; done?: boolean; children: React.ReactNode }) {
  return (
    <section aria-labelledby={`step-${step}`} className="border-t border-gray-300">
      <div className="flex items-start justify-between gap-4 pb-4 pt-4">
        <div>
          <h2 id={`step-${step}`} className="display text-2xl leading-tight text-gray-900">{title}</h2>
          {subtitle && <p className="mt-0.5 text-sm text-gray-700">{subtitle}</p>}
        </div>
        {done && (
          <span className="label-form mt-1.5 inline-flex shrink-0 items-center gap-1 !text-air-700">
            <CheckIcon className="h-4 w-4" /> Done
          </span>
        )}
      </div>
      <div className="pb-8">{children}</div>
    </section>
  )
}

// Part 1 and 2. What you are looking for

function Toggle({
  on, onClick, children, count,
}: { on: boolean; onClick: () => void; children: React.ReactNode; count?: number }) {
  return (
    <button
      type="button"
      aria-pressed={on}
      onClick={onClick}
      className={`chip py-1.5 ${on ? 'chip-on' : ''}`}
    >
      {on && <CheckIcon className="h-3.5 w-3.5" />}
      {children}
      {count !== undefined && (
        <span className={`text-xs tabular-nums ${on ? 'text-air-100' : 'text-gray-600'}`}>{count}</span>
      )}
    </button>
  )
}

const fieldClass = 'field mt-1.5'
const labelClass = 'label-form !text-gray-900'

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
        <p className="border-[1.5px] border-air-700 bg-air-50 px-3 py-2 text-sm text-air-900">
          We read your resume:{' '}
          {[found.program_label, degreeLabel, found.grad_year ? `graduating ${found.grad_year}` : '']
            .filter(Boolean).join(', ')}.
          {' '}Change anything that's wrong.
        </p>
      )}

      <div className="grid gap-4 sm:grid-cols-3">
        <div className="sm:col-span-3 md:col-span-1">
          <label htmlFor="pref-program" className={labelClass}>Program or major</label>
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
          <label htmlFor="pref-degree" className={labelClass}>Degree</label>
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
          <label htmlFor="pref-grad" className={labelClass}>Graduating in</label>
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
        <legend className={labelClass}>Looking for</legend>
        <div className="mt-1.5 inline-flex flex-wrap border-[1.5px] border-gray-900 bg-white">
          {LEVELS.map((l) => (
            <label
              key={l.value}
              className={`cursor-pointer px-3 py-1.5 text-sm font-semibold transition-colors ${
                prefs.level === l.value ? 'bg-gray-900 text-white' : 'text-gray-800 hover:bg-gray-100'
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
          <label htmlFor="pref-term" className={labelClass}>
            Co-op term <span className="font-normal normal-case tracking-normal text-gray-600">optional</span>
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
          <p className="mt-1 text-xs text-gray-600">Jobs for this term are ranked higher.</p>
        </div>
        <fieldset>
          <legend className={labelClass}>
            Co-op length <span className="font-normal normal-case tracking-normal text-gray-600">optional</span>
          </legend>
          <div className="mt-2 flex flex-wrap gap-2">
            {([4, 8, 12, 16] as const).map((d) => {
              const on = prefs.durations.includes(d)
              return (
                <button
                  key={d}
                  type="button"
                  role="checkbox"
                  aria-checked={on}
                  onClick={() =>
                    onChange({
                      ...prefs,
                      durations: on ? prefs.durations.filter((x) => x !== d) : [...prefs.durations, d],
                    })
                  }
                  className={`chip ${on ? 'chip-on' : ''}`}
                >
                  {d} months
                </button>
              )
            })}
          </div>
          <p className="mt-1 text-xs text-gray-600">Jobs of these lengths are ranked higher. Others still show.</p>
        </fieldset>
        <fieldset>
          <legend className={labelClass}>Countries</legend>
          <div className="mt-2.5 flex flex-wrap gap-4">
            {COUNTRIES.map((c) => (
              <label key={c.value} className="flex cursor-pointer items-center gap-2 text-sm text-gray-800">
                <input
                  type="checkbox"
                  className="h-4 w-4"
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
          <p className="mt-1.5 text-xs text-gray-600">US jobs here are internships and new grad roles.</p>
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
  /** What is saved on the server. null before the first upload */
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
        <legend className={labelClass}>Job type</legend>
        <p className="mb-2.5 mt-1 text-sm text-gray-700">
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
          {categories.length === 0 && <p className="text-sm text-gray-600">Loading job types...</p>}
        </div>
      </fieldset>

      <div>
        <label htmlFor="pref-keywords" className={labelClass}>
          Job title or keywords <span className="font-normal normal-case tracking-normal text-gray-600">optional</span>
        </label>
        <input
          id="pref-keywords"
          type="text"
          maxLength={100}
          value={prefs.keywords}
          onChange={(e) => onChange({ ...prefs, keywords: e.target.value })}
          placeholder="For example: data analyst, frontend, marketing"
          className={fieldClass}
        />
        <p className="mt-1 text-xs text-gray-600">Jobs that mention these are ranked higher.</p>
      </div>

      <div className="grid gap-6 sm:grid-cols-2">
        <div>
          <label htmlFor="pref-province" className={labelClass}>Where</label>
          <select
            id="pref-province"
            value={prefs.province}
            onChange={(e) => onChange({ ...prefs, province: e.target.value, city: '' })}
            className={fieldClass}
          >
            <option value="">Anywhere</option>
            {regions.map((p) => <option key={p} value={p}>{provinceName(p)}</option>)}
          </select>
          <p className="mt-1 text-xs text-gray-600">Remote jobs are always included.</p>
        </div>

        <fieldset>
          <legend className={labelClass}>Work mode</legend>
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
        <div className="flex flex-wrap items-center gap-3 border-t border-gray-200 pt-5">
          <button
            type="button"
            disabled={!dirty || update.isPending}
            onClick={() => update.mutate(prefs)}
            className="btn-primary"
          >
            {update.isPending ? 'Updating matches...' : 'Update my matches'}
          </button>
          {dirty && !update.isPending && <span className="text-sm text-gray-700">You changed your preferences.</span>}
          {update.isSuccess && !dirty && <span className="text-sm font-semibold text-air-700">Matches updated.</span>}
          {update.isError && <span role="alert" className="text-sm text-post-700">{update.error.message}</span>}
        </div>
      )}
    </div>
  )
}

// Part 3. Uploading

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
          setAuthOpen(true)  // this site needs an account
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
        className={`relative flex cursor-pointer border-[1.5px] transition-colors ${
          compact ? 'flex-col items-center px-4 py-4 text-center' : 'items-start justify-between gap-6 px-6 py-7 text-left sm:px-8'
        } ${dragging ? 'border-air-700 bg-air-50' : 'border-gray-900 bg-white hover:border-air-700 hover:bg-air-50'}`}
      >
        {busy ? (
          <span className="animate-pulse font-semibold text-air-800">
            Reading your resume and finding matching jobs...
          </span>
        ) : compact ? (
          <span className="flex items-center gap-2 text-sm text-gray-800">
            <UploadIcon className="h-4 w-4 text-air-700" />
            <span><span className="font-bold text-air-800">Drop your resume here</span> to replace it, or browse</span>
          </span>
        ) : (
          <>
            {/* Laid out like the front of an envelope. The words go where the address would and the file goes in the stamp corner */}
            <span className="min-w-0 pt-2">
              <span className="display block text-2xl text-gray-900 sm:text-[28px]">
                Drop your resume here, or <span className="text-air-700 underline underline-offset-4">browse</span>
              </span>
              <span className="mt-2 block border-t border-gray-300 pt-2 text-sm text-gray-700">PDF or Word (.docx), up to 5 MB. No sign up needed.</span>
            </span>
            <span className="flex h-24 w-20 shrink-0 rotate-3 flex-col items-center justify-center gap-1.5 border-2 border-dashed border-post-600 text-post-600" aria-hidden="true">
              <UploadIcon className="h-7 w-7" />
              <span className="stretch-condensed text-[10px] font-bold uppercase tracking-wider">PDF DOCX</span>
            </span>
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
      {error && <p role="alert" className="mt-2 text-sm font-semibold text-post-700">{error}</p>}
      {!compact && (
        <p className="mt-3 text-xs text-gray-600">
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
    <div className="mb-3 flex flex-wrap items-center justify-between gap-3 border-[1.5px] border-gray-900 px-4 py-3">
      <div className="flex min-w-0 items-center gap-3">
        <FileIcon className="h-5 w-5 shrink-0 text-air-700" />
        <div className="min-w-0">
          <p className="truncate text-sm font-bold text-gray-900">{resume.filename}</p>
          <p className="text-xs text-gray-600">Uploaded {formatDate(resume.uploaded_at)}</p>
        </div>
      </div>
      {confirm ? (
        <span className="flex items-center gap-2 text-sm">
          Delete your resume and matches?
          <button
            type="button"
            onClick={() => del.mutate(undefined, { onSuccess: () => setConfirm(false) })}
            disabled={del.isPending}
            className="btn-primary px-3 py-1"
          >
            {del.isPending ? 'Deleting...' : 'Delete'}
          </button>
          <button type="button" onClick={() => setConfirm(false)} className="btn-secondary px-3 py-1">
            Cancel
          </button>
        </span>
      ) : (
        <button type="button" onClick={() => setConfirm(true)} className="text-sm font-semibold text-gray-700 hover:text-post-700 hover:underline">
          Delete
        </button>
      )}
    </div>
  )
}

// Results. The matching jobs

/**
 * Plain words for the score. Students apply to lots of co-ops, so even lower scores read as
 * worth a try rather than a no.
 */
function scoreTone(score: number): { ring: string; label: string } {
  if (score >= 60) return { ring: 'text-post-600', label: 'Strong match' }
  if (score >= 35) return { ring: 'text-air-700', label: 'Good match' }
  return { ring: 'text-gray-600', label: 'Worth a try' }
}

function SkillList({ title, items, have }: { title: string; items: string[]; have: boolean }) {
  if (items.length === 0) return null
  return (
    <div>
      <p className="label-form mb-1.5">{title}</p>
      <ul className="flex flex-wrap gap-1.5" role="list">
        {items.map((s) => (
          <li
            key={s}
            className={`inline-flex items-center gap-1 rounded-sm border px-2 py-0.5 text-sm ${
              have ? 'border-air-200 bg-air-50 font-semibold text-air-900' : 'border-dashed border-gray-500 text-gray-800'
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
    <article className="border-b border-gray-300 py-6" aria-label={`${match.title} at ${match.company}`}>
      <div className="flex items-start gap-4">
        <div className="min-w-0 flex-1">
          <div className="flex flex-wrap items-start justify-between gap-x-4 gap-y-3">
            <div className="min-w-0">
              <Link to={`/postings/${match.posting_id}`} className="text-xl font-bold leading-snug text-gray-900 hover:text-air-700">
                <span className="mr-2 tabular-nums text-gray-400">{rank}</span>
                {match.title}
              </Link>
              <p className="mt-0.5 text-sm text-gray-700">
                {match.company}
                <span className="mx-1.5 text-gray-300" aria-hidden="true">|</span>
                <PinIcon className="mr-0.5 inline h-3.5 w-3.5 -translate-y-px text-gray-500" />
                {formatLocation(match.city, match.province, match.country)}
                {match.work_mode && match.city !== 'Remote' ? ` · ${workModeLabel(match.work_mode)}` : ''}
                {match.term && match.term !== 'Open' ? ` · ${match.term}` : ''}
                {match.duration_months ? ` · ${match.duration_months} months` : ''}
              </p>
            </div>
            <div className="flex items-center gap-2.5" aria-label={`Match score ${match.score} out of 100`}>
              <span
                className={`relative flex h-14 w-14 -rotate-6 flex-col items-center justify-center rounded-full border-2 border-current leading-none ${tone.ring}`}
              >
                <span className="absolute inset-[3px] rounded-full border border-current opacity-60" aria-hidden="true" />
                <span className="stretch-condensed text-xl font-extrabold tabular-nums">{match.score}</span>
                <span className="stretch-condensed text-[8px] font-bold uppercase tracking-wider">of 100</span>
              </span>
              <span className="label-form w-16 leading-tight">{tone.label}</span>
            </div>
          </div>

          {/* The free ranking's reason just repeats the skill lists below so only show reasons from the AI */}
          {!(hasSkills && /^(You have|None of its listed skills)/.test(match.reason)) && (
            <p className="mt-3 max-w-[70ch] text-[15px] text-gray-800">{match.reason}</p>
          )}

          {match.fit_notes.length > 0 && (
            <div className="mt-3">
              <p className="label-form mb-1.5">Why it fits</p>
              <ul className="grid gap-x-4 gap-y-1 text-sm text-gray-900 sm:grid-cols-2" role="list">
                {match.fit_notes.map((n) => (
                  <li key={n} className="flex items-start gap-1.5">
                    <CheckIcon className="mt-0.5 h-4 w-4 shrink-0 text-air-700" />
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

          <FitToggle postingId={match.posting_id} />

          <div className="mt-4 space-y-3 pt-1">
            <SaveAndApply postingId={match.posting_id} deadline={match.deadline} />
            <ConversationPanel postingId={match.posting_id} postingTitle={match.title} company={match.company} />
          </div>
        </div>
      </div>
    </article>
  )
}

/** Make your resume fit this job. Asks the server only when opened */
function FitToggle({ postingId }: { postingId: string }) {
  const [open, setOpen] = useState(false)
  return (
    <details className="mt-4 border-l-2 border-air-200 pl-4" onToggle={(e) => setOpen(e.currentTarget.open)}>
      <summary className="cursor-pointer text-[15px] font-bold text-air-700 hover:underline">
        Make your resume fit this job
      </summary>
      <div className="mt-3">
        <ResumeFitPanel postingId={postingId} enabled={open} />
      </div>
    </details>
  )
}

/** Open the job to apply or save it to the tracker. Saving twice does no harm on the server. */
function SaveAndApply({ postingId, deadline }: { postingId: string; deadline: string }) {
  const save = useSavePosting()
  return (
    <div className="flex flex-wrap items-center gap-x-4 gap-y-2 text-sm">
      <Link to={`/postings/${postingId}`} className="btn-primary px-3 py-1.5">
        View job and apply <ExternalIcon className="h-3.5 w-3.5" />
      </Link>
      {save.isSuccess ? (
        <Link to="/saved" className="inline-flex items-center gap-1 font-bold text-air-700 hover:underline">
          <CheckIcon className="h-4 w-4" /> Saved to tracker
        </Link>
      ) : (
        <button
          type="button"
          onClick={() => save.mutate(postingId)}
          disabled={save.isPending}
          className="btn-secondary px-3 py-1.5"
        >
          {save.isPending ? 'Saving...' : 'Save to tracker'}
        </button>
      )}
      {deadline && <span className="text-gray-600">Apply by {formatDate(deadline)}</span>}
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
        <p className="text-sm text-gray-700">
          {items.length > 0
            ? `${items.length} jobs, best fits first. Scores weigh your skills, program, graduation year, and the term and length you want. Apply widely: a lower score is still worth a try.`
            : null}
        </p>
        {canUseAi && items.length > 0 && (
          <button
            type="button"
            onClick={() => rematch.mutate()}
            disabled={rematch.isPending}
            className="btn-secondary px-3 py-1.5"
          >
            {rematch.isPending ? 'Ranking again, about 30 seconds...' : 'Rank again with my AI'}
          </button>
        )}
      </div>
      {rematch.isError && <p role="alert" className="text-sm font-semibold text-post-700">{rematch.error.message}</p>}

      {items.length === 0 ? (
        <div className="border-y border-gray-300 px-6 py-10 text-center">
          <p className="display text-xl text-gray-900">No open jobs fit yet</p>
          <p className="mt-1 text-sm text-gray-700">
            {narrowed
              ? 'Try more job types, "Anywhere", adding the United States, or "Co-op, internship or entry-level" above.'
              : 'New jobs are imported every few hours.'}{' '}
            You can also <Link to="/" className="link">browse all jobs</Link>.
          </p>
        </div>
      ) : (
        <ol className="border-t border-gray-300" aria-label="Matched jobs">
          {items.map((m, i) => <li key={m.posting_id}><MatchCard match={m} rank={i + 1} /></li>)}
        </ol>
      )}
    </div>
  )
}

// Results. Resume feedback

function Chips({ items }: { items: string[] }) {
  return (
    <ul className="flex flex-wrap gap-1.5" role="list">
      {items.map((s) => (
        <li key={s} className="inline-flex items-center gap-1 rounded-sm border border-air-200 bg-air-50 px-2 py-0.5 text-sm font-semibold text-air-900">
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
      <h4 className="label-form !text-gray-900">{title}</h4>
      <ul className="mt-1.5 list-disc space-y-1 pl-5 text-sm text-gray-800 marker:text-air-700">
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
            <h4 className="label-form !text-gray-900">Roles to search for</h4>
            <ul className="mt-2 flex flex-wrap gap-2" role="list">
              {review.roles_to_search.map((r) => (
                <li key={r}>
                  <Link
                    to={`/?q=${encodeURIComponent(r)}`}
                    className="chip"
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
          <h4 className="label-form !text-gray-900">Keywords to add, only if they're true for you</h4>
          <p className="mt-1 text-sm text-gray-800">{review.keywords_to_add.join(', ')}</p>
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
    return <div className="h-40 animate-pulse bg-gray-100" />
  }

  return (
    <div className="space-y-8">
      <div className="grid gap-8 border-t border-gray-300 pt-5 md:grid-cols-2">
        <div>
          <h3 className="flex items-center gap-2 text-lg font-extrabold text-gray-900">
            <CheckIcon className="h-5 w-5 text-air-700" /> Skills employers can see
          </h3>
          <p className="mb-3 mt-0.5 text-sm text-gray-700">On your resume and asked for in real job postings.</p>
          {data.skills_found.length > 0 ? (
            <Chips items={data.skills_found} />
          ) : (
            <p className="text-sm text-gray-800">
              We couldn't find any listed skills. Add a clear <strong>Skills</strong> section, for example
              "Python, SQL, React", so recruiters and filters can find them.
            </p>
          )}
        </div>
        <div>
          <h3 className="flex items-center gap-2 text-lg font-extrabold text-gray-900">
            <TrendIcon className="h-5 w-5 text-post-600" /> In demand, but not on your resume
          </h3>
          <p className="mb-3 mt-0.5 text-sm text-gray-700">
            The skills open jobs ask for most. Add the ones you have, or pick one to learn next.
          </p>
          {data.in_demand_missing.length > 0 ? (
            <ul className="divide-y divide-gray-200 border-y border-gray-200" role="list">
              {data.in_demand_missing.map((m) => (
                <li key={m.skill} className="flex items-center justify-between py-1.5 text-sm">
                  <span className="font-semibold text-gray-900">{m.skill}</span>
                  <span className="tabular-nums text-gray-600">{m.postings} job{m.postings === 1 ? '' : 's'}</span>
                </li>
              ))}
            </ul>
          ) : (
            <p className="text-sm text-gray-800">You already list the most requested skills.</p>
          )}
        </div>
      </div>

      <div className="space-y-4 border-t border-gray-300 pt-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <h3 className="text-lg font-extrabold text-gray-900">Full resume review</h3>
            <p className="text-sm text-gray-700">
              Strengths, what to fix, how to tailor it, and roles to search for, written for your resume.
            </p>
          </div>
          {canUseAi ? (
            <button
              type="button"
              onClick={() => generate.mutate()}
              disabled={generate.isPending}
              className="btn-primary"
            >
              {generate.isPending ? 'Reviewing, about 20 seconds...' : data.ai ? 'Refresh review' : 'Review my resume'}
            </button>
          ) : (
            <Link to="/ai-key" className="btn-primary">
              Add a free AI key
            </Link>
          )}
        </div>
        {!canUseAi && !data.ai && (
          <p className="text-sm text-gray-700">
            This part uses your own Claude, ChatGPT or Gemini key. Gemini has a free tier, and setup takes about two minutes.
          </p>
        )}
        {aiKey && !data.ai && !generate.isPending && (
          <p className="text-xs text-gray-600">Runs on your {providerName(aiKey.provider)} key ({aiKey.model}).</p>
        )}
        {generate.isError && <p role="alert" className="text-sm font-semibold text-post-700">{generate.error.message}</p>}
        {data.ai && <AiReview review={data.ai} />}
      </div>
    </div>
  )
}

// The page

export default function ResumePage() {
  const { data: me, isLoading: meLoading } = useMe()
  const { data, isLoading } = useMatches(Boolean(me))
  const resume = data?.resume ?? null
  const savedPrefs = data?.preferences ?? null
  const education = data?.education ?? null
  const [prefs, setPrefs] = useState<JobPreferences>(loadLocalPrefs)
  const [tab, setTab] = useState<'jobs' | 'feedback'>('jobs')

  // Once there is a resume the form starts from what is saved with it
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
    <div className="mx-auto max-w-4xl px-4 py-8 sm:py-10">
      <header className="pb-8">
        <h1 className="display text-4xl leading-[1.02] text-gray-900 sm:text-5xl">Find co-op jobs that fit you</h1>
        <p className="mt-3 max-w-2xl text-[17px] text-gray-700">
          Tell us about your studies and what you want, upload your resume, and see the jobs you're a
          good fit for. We match your program, graduation year and skills against what each job
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
          <div className="h-32 animate-pulse bg-gray-100" />
        ) : (
          <>
            {resume && <StoredResume resume={resume} />}
            <ResumeDropzone compact={Boolean(resume)} prefs={prefs} />
          </>
        )}
      </StepCard>

      {resume && (
        <section aria-label="Results" className="space-y-5 pt-2">
          <div className="flex gap-0 bg-gray-100" role="tablist">
            <TabButton active={tab === 'jobs'} onClick={() => setTab('jobs')} id="jobs">
              Jobs that fit your resume <span className="ml-1 tabular-nums opacity-80">{items.length}</span>
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
      className={`px-4 py-3 text-[15px] font-bold transition-colors ${
        active ? 'bg-post-600 text-white' : 'text-gray-800 hover:bg-gray-200'
      }`}
    >
      {children}
    </button>
  )
}
