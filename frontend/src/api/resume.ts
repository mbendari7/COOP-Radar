/**
 * TanStack Query hooks for the resume + match API.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { aiHeaders } from './aiKey'
import { API_BASE, apiFetch, toApiError } from './client'

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
  score: number        // 0–100
  reason: string
}

export interface UploadResponse {
  resume: ResumeOut
  matches: MatchResultOut[]
}

export interface MatchesResponse {
  items: MatchResultOut[]
  resume: ResumeOut | null
}

// ── Fetchers ──────────────────────────────────────────────────────────────────

const fetchMatches = () => apiFetch<MatchesResponse>('/api/resume/matches')

function uploadResumeFile(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  return apiFetch<UploadResponse>('/api/resume', { method: 'POST', body: form, headers: aiHeaders() })
}

const deleteResumeFile = () => apiFetch<void>('/api/resume', { method: 'DELETE' })

// ── Hooks ─────────────────────────────────────────────────────────────────────

/** Get stored ranked match results. Returns empty list when no resume on file. */
export function useMatches() {
  return useQuery({
    queryKey: ['matches'],
    queryFn: fetchMatches,
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
    },
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
    },
  })
}

// ── SSE streaming Q&A ─────────────────────────────────────────────────────────

/**
 * Ask a question about a matched posting using SSE streaming.
 * Calls onDelta for each token, onDone when stream ends, onError on failure.
 */
export async function askAboutPosting(
  postingId: string,
  question: string,
  onDelta: (token: string) => void,
  onDone: () => void,
  onError: (err: Error) => void,
): Promise<void> {
  try {
    const res = await fetch(`${API_BASE}/api/resume/matches/${postingId}/ask`, {
      method: 'POST',
      headers: { 'Content-Type': 'application/json', ...aiHeaders() },
      body: JSON.stringify({ question }),
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
