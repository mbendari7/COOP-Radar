/**
 * TanStack Query hooks for saved postings.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { PostingListItem } from './postings'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

// ── Types ─────────────────────────────────────────────────────────────────────

export type ApplicationStatus = 'applied' | 'interviewing' | 'offer' | 'rejected'

export interface SavedPostingOut {
  id: string
  saved_at: string
  status: ApplicationStatus | null
  posting: PostingListItem
}

export interface SavedPostingsPage {
  items: SavedPostingOut[]
  total: number
  page: number
  page_size: number
  status_counts: Record<string, number>
}

export interface SavedListParams {
  status?: ApplicationStatus
  page?: number
  page_size?: number
}

// ── Fetchers ──────────────────────────────────────────────────────────────────

async function fetchSaved(params: SavedListParams): Promise<SavedPostingsPage> {
  const sp = new URLSearchParams()
  if (params.status) sp.set('status', params.status)
  if (params.page && params.page !== 1) sp.set('page', String(params.page))
  if (params.page_size && params.page_size !== 25) sp.set('page_size', String(params.page_size))
  const qs = sp.toString() ? `?${sp}` : ''

  const res = await fetch(`${API_BASE}/api/saved${qs}`, { credentials: 'include' })
  if (!res.ok) throw new Error(`GET /api/saved failed: ${res.status}`)
  return res.json() as Promise<SavedPostingsPage>
}

async function postSave(postingId: string): Promise<SavedPostingOut> {
  const res = await fetch(`${API_BASE}/api/saved`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ posting_id: postingId }),
  })
  if (!res.ok) throw new Error(`POST /api/saved failed: ${res.status}`)
  return res.json() as Promise<SavedPostingOut>
}

async function deleteSave(savedId: string): Promise<void> {
  const res = await fetch(`${API_BASE}/api/saved/${savedId}`, {
    method: 'DELETE',
    credentials: 'include',
  })
  if (!res.ok && res.status !== 404) throw new Error(`DELETE /api/saved/${savedId} failed: ${res.status}`)
}

async function patchStatus(savedId: string, status: ApplicationStatus | null): Promise<SavedPostingOut> {
  const res = await fetch(`${API_BASE}/api/saved/${savedId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ status }),
  })
  if (!res.ok) throw new Error(`PATCH /api/saved/${savedId}/status failed: ${res.status}`)
  return res.json() as Promise<SavedPostingOut>
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useSavedPostings(params: SavedListParams = {}) {
  return useQuery({
    queryKey: ['saved', params],
    queryFn: () => fetchSaved(params),
    retry: false,
  })
}

export function useSavePosting() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: postSave,
    onSuccess: () => {
      // Invalidate both lists so is_saved and the saved page stay in sync
      qc.invalidateQueries({ queryKey: ['saved'] })
      qc.invalidateQueries({ queryKey: ['postings'] })
    },
  })
}

export function useUnsavePosting() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: deleteSave,
    onSuccess: () => {
      qc.invalidateQueries({ queryKey: ['saved'] })
      qc.invalidateQueries({ queryKey: ['postings'] })
    },
  })
}

export function useUpdateStatus() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ savedId, status }: { savedId: string; status: ApplicationStatus | null }) =>
      patchStatus(savedId, status),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['saved'] }),
  })
}
