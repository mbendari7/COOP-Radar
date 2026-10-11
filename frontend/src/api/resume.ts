/**
 * TanStack Query hooks for the resume + match API.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

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

async function fetchResume(): Promise<ResumeOut> {
  const res = await fetch(`${API_BASE}/api/resume`, { credentials: 'include' })
  if (res.status === 404) throw new Error('RESUME_NOT_FOUND')
  if (!res.ok) throw new Error(`GET /api/resume failed: ${res.status}`)
  return res.json() as Promise<ResumeOut>
}

async function fetchMatches(): Promise<MatchesResponse> {
  const res = await fetch(`${API_BASE}/api/resume/matches`, { credentials: 'include' })
  if (!res.ok) throw new Error(`GET /api/resume/matches failed: ${res.status}`)
  return res.json() as Promise<MatchesResponse>
}

async function uploadResumeFile(file: File): Promise<UploadResponse> {
  const form = new FormData()
  form.append('file', file)
  const res = await fetch(`${API_BASE}/api/resume`, {
    method: 'POST',
    body: form,
    credentials: 'include',
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({})) as { detail?: { code?: string; detail?: string } | string }
    const detail = typeof body.detail === 'object' ? body.detail : { detail: String(body.detail ?? 'Upload failed') }
    throw Object.assign(new Error(detail.detail ?? 'Upload failed'), { code: detail.code })
  }
  return res.json() as Promise<UploadResponse>
}

async function deleteResumeFile(): Promise<void> {
  const res = await fetch(`${API_BASE}/api/resume`, {
    method: 'DELETE',
    credentials: 'include',
  })
  if (res.status === 404) throw new Error('RESUME_NOT_FOUND')
  if (!res.ok) throw new Error(`DELETE /api/resume failed: ${res.status}`)
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

/** Get stored resume metadata. Throws if none on file (404 → error state). */
export function useResume() {
  return useQuery({
    queryKey: ['resume'],
    queryFn: fetchResume,
    retry: (count, err) => {
      if (err instanceof Error && err.message === 'RESUME_NOT_FOUND') return false
      return count < 2
    },
  })
}

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
      headers: { 'Content-Type': 'application/json' },
      body: JSON.stringify({ question }),
      credentials: 'include',
    })

    if (!res.ok) {
      const body = await res.json().catch(() => ({})) as { detail?: { detail?: string } | string }
      const msg = typeof body.detail === 'object'
        ? (body.detail.detail ?? 'Request failed')
        : String(body.detail ?? 'Request failed')
      throw new Error(msg)
    }

    if (!res.body) throw new Error('No response body')

    const reader = res.body.getReader()
    const decoder = new TextDecoder()
    let buffer = ''

    while (true) {
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
        try {
          const parsed = JSON.parse(payload) as { delta?: string }
          if (parsed.delta) onDelta(parsed.delta)
        } catch {
          // skip malformed SSE lines
        }
      }
    }
    onDone()
  } catch (err) {
    onError(err instanceof Error ? err : new Error(String(err)))
  }
}
