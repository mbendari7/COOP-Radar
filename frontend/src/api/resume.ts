/**
 * TanStack Query hooks for the resume and matching API.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { aiHeaders } from './aiKey'
import { API_BASE, apiFetch, toApiError } from './client'
import type { CategoryKey, CountryCode, ProgramKey, WorkMode } from './postings'

// Types

export interface ResumeOut {
  id: string
  filename: string
  file_size: number
  uploaded_at: string  // ISO datetime
}

export interface MatchResultOut {
  posting_id: string
  title: string
  company: string
  city: string
  province: string
  term: string
  deadline: string
  score: number        // 0 to 100
  reason: string
  work_mode: string
  /** The job's skills that the resume shows and the ones it does not */
  matched_skills: string[]
  missing_skills: string[]
  country: string
  /** Why the job fits, read from its description. Role, program, grad year, term and skills */
  fit_notes: string[]
}

export type Degree = '' | 'diploma' | 'bachelors' | 'masters' | 'phd'

/** What we read from the education part of the resume. Empty or null when not found */
export interface DetectedEducation {
  program: ProgramKey | ''
  program_label: string
  degree: Degree
  grad_year: number | null
}

/** What the student is looking for. Matching only looks at jobs that fit. */
export interface JobPreferences {
  categories: CategoryKey[]
  keywords: string
  province: string
  city: string
  work_modes: WorkMode[]
  /** entry is students plus entry level, students is co-op and intern only, all is everything */
  level: 'entry' | 'students' | 'all'
  /** About the student. Blank means read it from the resume */
  program: ProgramKey | ''
  degree: Degree
  grad_year: number | null
  /** The co-op term they want, like Summer 2027 */
  term: string
  countries: CountryCode[]
}

export const DEFAULT_PREFERENCES: JobPreferences = {
  categories: [], keywords: '', province: '', city: '', work_modes: [], level: 'students',
  program: '', degree: '', grad_year: null, term: '', countries: ['CA'],
}

export interface UploadResponse {
  resume: ResumeOut
  matches: MatchResultOut[]
  preferences?: JobPreferences | null
  education?: DetectedEducation | null
}

export interface MatchesResponse {
  items: MatchResultOut[]
  resume: ResumeOut | null
  preferences?: JobPreferences | null
  education?: DetectedEducation | null
}

export interface DemandSkill {
  skill: string
  /** How many open jobs ask for it */
  postings: number
}

export interface AIInsights {
  summary: string
  strengths: string[]
  improvements: string[]
  tailoring_tips: string[]
  roles_to_search: string[]
  keywords_to_add: string[]
}

export interface ResumeInsights {
  skills_found: string[]
  in_demand_missing: DemandSkill[]
  /** null until the visitor runs the AI review */
  ai: AIInsights | null
}

/** What the per-job assistant should do */
export type AskMode = 'question' | 'tailor' | 'cover_letter'

// Calls to the server

const fetchMatches = () => apiFetch<MatchesResponse>('/api/resume/matches')

function uploadResumeFile({ file, preferences }: { file: File; preferences?: JobPreferences }): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  if (preferences) form.append('preferences', JSON.stringify(preferences))
  return apiFetch<UploadResponse>('/api/resume', { method: 'POST', body: form, headers: aiHeaders() })
}

const deleteResumeFile = () => apiFetch<void>('/api/resume', { method: 'DELETE' })

// Hooks

/** The saved ranked matches. An empty list when there is no resume yet. */
export function useMatches(enabled = true) {
  return useQuery({
    queryKey: ['matches'],
    queryFn: fetchMatches,
    enabled,
  })
}

/** Upload a resume file. When it works the resume and matches get fetched again. */
export function useUploadResume() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: uploadResumeFile,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['resume'] })
      void queryClient.invalidateQueries({ queryKey: ['matches'] })
      void queryClient.invalidateQueries({ queryKey: ['insights'] })
    },
  })
}

/** Save what the student is looking for and match the saved resume again for free. */
export function useUpdatePreferences() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: (preferences: JobPreferences) =>
      apiFetch<UploadResponse>('/api/resume/preferences', {
        method: 'PUT',
        headers: aiHeaders(),
        json: preferences,
      }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['matches'] }),
  })
}

/** Free insights like skills found and popular skills missing, plus the saved AI review. */
export function useInsights(enabled: boolean) {
  return useQuery({
    queryKey: ['insights'],
    queryFn: () => apiFetch<ResumeInsights>('/api/resume/insights'),
    enabled,
  })
}

/** Run the AI resume review on the visitor's key. The server saves the result. */
export function useGenerateInsights() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<ResumeInsights>('/api/resume/insights', { method: 'POST', headers: aiHeaders() }),
    onSuccess: (data) => queryClient.setQueryData(['insights'], data),
  })
}

/** Rank the saved resume against today's jobs again with the visitor's AI. */
export function useRematch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<UploadResponse>('/api/resume/rematch', { method: 'POST', headers: aiHeaders() }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['matches'] }),
  })
}

/** Delete the saved resume. When it works the resume and matches get fetched again. */
export function useDeleteResume() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: deleteResumeFile,
    onSuccess: () => {
      void queryClient.invalidateQueries({ queryKey: ['resume'] })
      void queryClient.invalidateQueries({ queryKey: ['matches'] })
      void queryClient.invalidateQueries({ queryKey: ['insights'] })
    },
  })
}

// Streamed answers about a job

/**
 * Ask about a matched job and get the answer streamed back.
 * mode question answers `question`. tailor and cover_letter need no question.
 * Calls onDelta for each piece, onDone at the end and onError if it fails.
 */
export async function askAboutPosting(
  postingId: string,
  question: string,
  onDelta: (token: string) => void,
  onDone: () => void,
  onError: (err: Error) => void,
  mode: AskMode = 'question',
): Promise<void> {
  try {
    const res = await fetch(`${API_BASE}/api/resume/matches/${postingId}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...aiHeaders() },
      body: JSON.stringify({ question, mode }),
      credentials: 'include',
    })

    if (!res.ok) throw await toApiError(res)

    if (!res.body) throw new Error('No response body')

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    for (;;) {
      const { done, value } = await reader.read()
      if (done) break
      buffer += decoder.decode(value, { stream: true })

      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        if (!line.startsWith('data: ')) continue
        const payload = line.slice(6).trim()
        if (payload === '[DONE]') {
          onDone()
          return
        }
        let parsed: { delta?: string; error?: string }
        try {
          parsed = JSON.parse(payload) as { delta?: string; error?: string }
        } catch {
          continue // skip broken lines
        }
        // Once streaming starts the backend reports errors inside the stream
        if (parsed.error) throw new Error(parsed.error)
        if (parsed.delta) onDelta(parsed.delta)
      }
    }
    onDone()
  } catch (err) {
    onError(err instanceof Error ? err : new Error(String(err)))
  }
}
