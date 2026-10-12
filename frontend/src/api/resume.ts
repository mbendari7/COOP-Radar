/**
 * TanStack Query hooks for the resume + match API.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { aiHeaders } from './aiKey'
import { API_BASE, apiFetch, toApiError } from './client'
import type { CategoryKey, WorkMode } from './postings'

// ── Types ─────────────────────────────────────────────────────────────────────

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
  score: number        // 0-100
  reason: string
  work_mode: string
  /** The posting's skills that the resume shows, and the ones it doesn't */
  matched_skills: string[]
  missing_skills: string[]
}

/** What the student is looking for; matching only considers jobs that fit. */
export interface JobPreferences {
  categories: CategoryKey[]
  keywords: string
  province: string
  city: string
  work_modes: WorkMode[]
  /** entry: students + entry-level · students: co-op/intern only · all */
  level: 'entry' | 'students' | 'all'
}

export const DEFAULT_PREFERENCES: JobPreferences = {
  categories: [], keywords: '', province: '', city: '', work_modes: [], level: 'entry',
}

export interface UploadResponse {
  resume: ResumeOut
  matches: MatchResultOut[]
}

export interface MatchesResponse {
  items: MatchResultOut[]
  resume: ResumeOut | null
  preferences?: JobPreferences | null
}

export interface DemandSkill {
  skill: string
  /** How many open postings ask for it */
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

// ── Fetchers ──────────────────────────────────────────────────────────────────

const fetchMatches = () => apiFetch<MatchesResponse>('/api/resume/matches')

function uploadResumeFile({ file, preferences }: { file: File; preferences?: JobPreferences }): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  if (preferences) form.append('preferences', JSON.stringify(preferences))
  return apiFetch<UploadResponse>('/api/resume', { method: 'POST', body: form, headers: aiHeaders() })
}

const deleteResumeFile = () => apiFetch<void>('/api/resume', { method: 'DELETE' })

// ── Hooks ─────────────────────────────────────────────────────────────────────

/** Get stored ranked match results. Returns empty list when no resume on file. */
export function useMatches(enabled = true) {
  return useQuery({
    queryKey: ['matches'],
    queryFn: fetchMatches,
    enabled,
  })
}

/** Upload a resume file; on success invalidates resume + matches queries. */
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

/** Save what the student is looking for and re-match the stored resume (free). */
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

/** Free insights (skills found, in-demand skills missing) plus the cached AI review. */
export function useInsights(enabled: boolean) {
  return useQuery({
    queryKey: ['insights'],
    queryFn: () => apiFetch<ResumeInsights>('/api/resume/insights'),
    enabled,
  })
}

/** Run the AI resume review with the visitor's key; the result is cached server-side. */
export function useGenerateInsights() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<ResumeInsights>('/api/resume/insights', { method: 'POST', headers: aiHeaders() }),
    onSuccess: (data) => queryClient.setQueryData(['insights'], data),
  })
}

/** Re-rank the stored resume against current postings with the visitor's AI. */
export function useRematch() {
  const queryClient = useQueryClient()
  return useMutation({
    mutationFn: () =>
      apiFetch<UploadResponse>('/api/resume/rematch', { method: 'POST', headers: aiHeaders() }),
    onSuccess: () => void queryClient.invalidateQueries({ queryKey: ['matches'] }),
  })
}

/** Delete the stored resume; on success invalidates resume + matches queries. */
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

// ── SSE streaming Q&A ─────────────────────────────────────────────────────────

/**
 * Ask about a matched posting using SSE streaming.
 * mode 'question' answers `question`; 'tailor' and 'cover_letter' need no question.
 * Calls onDelta for each token, onDone when stream ends, onError on failure.
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
          continue // skip malformed SSE lines
        }
        // The backend reports failures in-band once streaming has started
        if (parsed.error) throw new Error(parsed.error)
        if (parsed.delta) onDelta(parsed.delta)
      }
    }
    onDone()
  } catch (err) {
    onError(err instanceof Error ? err : new Error(String(err)))
  }
}
