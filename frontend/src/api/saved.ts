/**
 * TanStack Query hooks for saved postings, events, and CSV export.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import type { PostingListItem } from './postings'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

// ── Types ─────────────────────────────────────────────────────────────────────

export type ApplicationStatus =
  | 'saved'
  | 'applying'
  | 'applied'
  | 'interview'
  | 'offer'
  | 'rejected'
  | 'withdrawn'

export const STATUS_LABELS: Record<ApplicationStatus, string> = {
  saved: 'Saved',
  applying: 'Applying',
  applied: 'Applied',
  interview: 'Interview',
  offer: 'Offer',
  rejected: 'Rejected',
  withdrawn: 'Withdrawn',
}

export const ALL_STATUSES: ApplicationStatus[] = [
  'saved', 'applying', 'applied', 'interview', 'offer', 'rejected', 'withdrawn',
]

export interface ApplicationEventOut {
  id: string
  status: ApplicationStatus
  notes: string | null
  event_date: string | null
  created_at: string
}

export interface SavedPostingOut {
  id: string
  saved_at: string
  last_status_at: string | null
  status: ApplicationStatus | null
  posting: PostingListItem
  events: ApplicationEventOut[]
}

export interface DeadlineItem {
  saved_id: string
  posting_id: string
  title: string
  company: string
  deadline: string
}

export interface SavedPostingsPage {
  items: SavedPostingOut[]
  total: number
  page: number
  page_size: number
  status_counts: Record<string, number>
  total_applied: number
  total_interview: number
  total_offer: number
  deadlines_this_week: DeadlineItem[]
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

async function patchStatus(
  savedId: string,
  statusVal: ApplicationStatus | null,
  notes?: string | null,
  eventDate?: string | null,
): Promise<SavedPostingOut> {
  const res = await fetch(`${API_BASE}/api/saved/${savedId}/status`, {
    method: 'PATCH',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ status: statusVal, notes: notes ?? null, event_date: eventDate ?? null }),
  })
  if (!res.ok) throw new Error(`PATCH /api/saved/${savedId}/status failed: ${res.status}`)
  return res.json() as Promise<SavedPostingOut>
}

async function postEvent(
  savedId: string,
  status: ApplicationStatus,
  notes: string | null,
  eventDate: string | null,
): Promise<SavedPostingOut> {
  const res = await fetch(`${API_BASE}/api/saved/${savedId}/events`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify({ status, notes, event_date: eventDate }),
  })
  if (!res.ok) throw new Error(`POST /api/saved/${savedId}/events failed: ${res.status}`)
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
    mutationFn: ({
      savedId,
      status: statusVal,
      notes,
      eventDate,
    }: {
      savedId: string
      status: ApplicationStatus | null
      notes?: string | null
      eventDate?: string | null
    }) => patchStatus(savedId, statusVal, notes, eventDate),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['saved'] }),
  })
}

export function useAddEvent() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({
      savedId,
      status: statusVal,
      notes,
      eventDate,
    }: {
      savedId: string
      status: ApplicationStatus
      notes: string | null
      eventDate: string | null
    }) => postEvent(savedId, statusVal, notes, eventDate),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['saved'] }),
  })
}

/** Trigger a CSV download — opens the export URL in a new tab. */
export function downloadCsv(): void {
  window.open(`${API_BASE}/api/saved/export/csv`, '_blank')
}
