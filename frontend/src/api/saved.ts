/**
 * TanStack Query hooks for saved jobs, their history and the CSV download.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { API_BASE, ApiError, apiFetch } from './client'
import type { PostingListItem } from './postings'

// Types

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

// Calls to the server

function fetchSaved(params: SavedListParams): Promise<SavedPostingsPage> {
  const sp = new URLSearchParams()
  if (params.status) sp.set('status', params.status)
  if (params.page && params.page !== 1) sp.set('page', String(params.page))
  if (params.page_size && params.page_size !== 25) sp.set('page_size', String(params.page_size))
  const qs = sp.toString() ? `?${sp}` : ''
  return apiFetch<SavedPostingsPage>(`/api/saved${qs}`)
}

const postSave = (postingId: string) =>
  apiFetch<SavedPostingOut>('/api/saved', { method: 'POST', json: { posting_id: postingId } })

async function deleteSave(savedId: string): Promise<void> {
  try {
    await apiFetch<void>(`/api/saved/${savedId}`, { method: 'DELETE' })
  } catch (err) {
    // Already gone counts as done, like when it was unsaved in another tab
    if (!(err instanceof ApiError && err.status === 404)) throw err
  }
}

const patchStatus = (
  savedId: string,
  statusVal: ApplicationStatus | null,
  notes?: string | null,
  eventDate?: string | null,
) =>
  apiFetch<SavedPostingOut>(`/api/saved/${savedId}/status`, {
    method: 'PATCH',
    json: { status: statusVal, notes: notes ?? null, event_date: eventDate ?? null },
  })

const postEvent = (
  savedId: string,
  status: ApplicationStatus,
  notes: string | null,
  eventDate: string | null,
) =>
  apiFetch<SavedPostingOut>(`/api/saved/${savedId}/events`, {
    method: 'POST',
    json: { status, notes, event_date: eventDate },
  })

// Hooks

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
      qc.invalidateQueries({ queryKey: ['posting'] })
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
      qc.invalidateQueries({ queryKey: ['posting'] })
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

/** Start a CSV download. The browser sends the session cookie along with it. */
export function downloadCsv(): void {
  window.open(`${API_BASE}/api/saved/export/csv`, '_blank')
}
