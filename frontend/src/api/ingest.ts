/**
 * TanStack Query hooks for admin ingest source management.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

// ── Types ─────────────────────────────────────────────────────────────────────

export interface IngestSourceOut {
  id: string
  name: string
  adapter_type: string
  enabled: boolean
  auto_paused: boolean
  last_run_at: string | null
  last_run_status: string | null
  last_run_added: number | null
  last_run_updated: number | null
  last_run_closed: number | null
  last_run_errors: number | null
}

export interface IngestRunOut {
  id: string
  started_at: string
  finished_at: string | null
  status: string
  added: number
  updated: number
  closed: number
  errors: number
  error_log: string[]
}

export interface RunsPage {
  items: IngestRunOut[]
  total: number
  page: number
  page_size: number
}

export interface TriggerRunOut {
  run_id: string
  message: string
}

export interface SourcePatchIn {
  enabled?: boolean
  auto_paused?: boolean
}

// ── Fetchers ──────────────────────────────────────────────────────────────────

async function fetchAdminSources(): Promise<IngestSourceOut[]> {
  const res = await fetch(`${API_BASE}/api/admin/sources`, { credentials: 'include' })
  if (res.status === 403) throw new Error('FORBIDDEN')
  if (!res.ok) throw new Error(`GET /api/admin/sources failed: ${res.status}`)
  return res.json() as Promise<IngestSourceOut[]>
}

async function fetchRunHistory(sourceId: string, page = 1): Promise<RunsPage> {
  const res = await fetch(
    `${API_BASE}/api/admin/sources/${sourceId}/runs?page=${page}`,
    { credentials: 'include' }
  )
  if (!res.ok) throw new Error(`GET /api/admin/sources/${sourceId}/runs failed: ${res.status}`)
  return res.json() as Promise<RunsPage>
}

async function postTriggerRun(sourceId: string): Promise<TriggerRunOut> {
  const res = await fetch(`${API_BASE}/api/admin/sources/${sourceId}/run`, {
    method: 'POST',
    credentials: 'include',
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body?.detail?.code ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<TriggerRunOut>
}

async function patchSource(sourceId: string, data: SourcePatchIn): Promise<IngestSourceOut> {
  const res = await fetch(`${API_BASE}/api/admin/sources/${sourceId}`, {
    method: 'PATCH',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify(data),
  })
  if (!res.ok) throw new Error(`PATCH /api/admin/sources/${sourceId} failed: ${res.status}`)
  return res.json() as Promise<IngestSourceOut>
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

export function useAdminSources() {
  return useQuery({
    queryKey: ['adminSources'],
    queryFn: fetchAdminSources,
    staleTime: 30 * 1000,
  })
}

export function useRunHistory(sourceId: string | undefined, page = 1) {
  return useQuery({
    queryKey: ['runHistory', sourceId, page],
    queryFn: () => fetchRunHistory(sourceId!, page),
    enabled: !!sourceId,
    staleTime: 15 * 1000,
  })
}

export function useTriggerRun() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (sourceId: string) => postTriggerRun(sourceId),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['adminSources'] })
    },
  })
}

export function usePatchSource() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: ({ sourceId, data }: { sourceId: string; data: SourcePatchIn }) =>
      patchSource(sourceId, data),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['adminSources'] })
    },
  })
}
