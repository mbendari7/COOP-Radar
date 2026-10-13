/**
 * TanStack Query hooks for the admin page that manages import sources.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

import { apiFetch } from './client'

// Types

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

// Calls to the server

const fetchAdminSources = () => apiFetch<IngestSourceOut[]>('/api/admin/sources')

const fetchRunHistory = (sourceId: string, page = 1) =>
  apiFetch<RunsPage>(`/api/admin/sources/${sourceId}/runs?page=${page}`)

const postTriggerRun = (sourceId: string) =>
  apiFetch<TriggerRunOut>(`/api/admin/sources/${sourceId}/run`, { method: 'POST' })

const patchSource = (sourceId: string, data: SourcePatchIn) =>
  apiFetch<IngestSourceOut>(`/api/admin/sources/${sourceId}`, { method: 'PATCH', json: data })

// Hooks

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
      void qc.invalidateQueries({ queryKey: ['runHistory'] })
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
