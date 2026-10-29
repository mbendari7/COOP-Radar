/**
 * TanStack Query hooks for the postings API.
 *
 * Types mirror the backend Pydantic schemas (app/schemas/posting.py). To regenerate
 * them from the live OpenAPI schema run `npm run gen:api` (writes src/api/types.gen.ts).
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { useEffect } from 'react'
import { API_BASE, apiFetch } from './client'
import type { components } from './types.gen'

// Types

// Response types come from the backend's OpenAPI schema (src/api/types.gen.ts), so they can't
// drift from the Pydantic models. Regenerate after changing a schema:
//   cd backend && python -m scripts.export_openapi && cd ../frontend && npm run gen:api
type Schemas = components['schemas']

export type WorkMode = Schemas['WorkMode']
/** `source_id` is there for jobs that came live from an employer's career board. `is_saved` only when signed in */
export type PostingListItem = Schemas['PostingListItem']
export type PostingDetail = Schemas['PostingDetail']
export type SimilarPostingOut = Schemas['SimilarPostingOut']
export type SimilarPostingsResponse = Schemas['SimilarPostingsResponse']
export type PostingsPage = Schemas['Page_PostingListItem_']
export type FilterMeta = Schemas['FilterMeta']
/** The first page of jobs and the filter choices, the same for everyone so a CDN can keep it */
export type PostingsSnapshot = Schemas['PostingsSnapshot']
export type CategoryCount = Schemas['CategoryCount']
/** Job type keys like software and data, worked out from job titles on the server */
export type CategoryKey = CategoryCount['key']
/** Programs a student can pick, like computer_science and business */
export type ProgramOption = Schemas['ProgramOption']
export type ProgramKey = ProgramOption['key']
export type CountryCode = 'CA' | 'US'
/** Co-op, internship, new grad or regular job, judged by the title */
export type RoleType = PostingListItem['role']
export type SearchMode = 'keyword' | 'semantic'
/** winter, spring, summer or fall, read from the job's term */
export type Season = NonNullable<PostingListItem['season']>

export type SortField =
  | 'posted_at' | 'deadline' | 'company' | 'title' | 'duration_months' | 'term_start' | 'first_seen_at'
export type SortOrder = 'asc' | 'desc'
export type PageSize = 10 | 25 | 50 | 100

export interface PostingListParams {
  q?: string
  city?: string
  province?: string
  term?: string
  /** Term seasons, any of them */
  season?: Season[]
  work_mode?: WorkMode
  duration?: number[]
  skills?: string[]
  category?: CategoryKey[]
  company?: string[]
  /** Only jobs posted in the last N days (1, 3, 7, 14 or 30) */
  posted_within?: number
  /** Only jobs CoopRadar first saw after this moment (ISO date and time) */
  added_since?: string
  /** With a term or length picked, also show jobs that don't say theirs, after the ones that match */
  include_unstated?: boolean
  /** Countries to include. None means all */
  country?: CountryCode[]
  /** Jobs for a program. Named in the description or fitting its job types */
  program?: ProgramKey
  /** Hide jobs asking for a different graduation year */
  grad_year?: number
  show_expired?: boolean
  show_closed?: boolean
  /** Only intern, co-op, student and new grad roles */
  students_only?: boolean
  /** Hide senior, staff, lead and manager roles */
  hide_senior?: boolean
  search_mode?: SearchMode
  sort?: SortField
  order?: SortOrder
  page?: number
  page_size?: PageSize
}

// Calls to the server

function buildQueryString(params: PostingListParams): string {
  const sp = new URLSearchParams()

  if (params.q) sp.set('q', params.q)
  if (params.city) sp.set('city', params.city)
  if (params.province) sp.set('province', params.province)
  if (params.term) sp.set('term', params.term)
  params.season?.forEach((s) => sp.append('season', s))
  if (params.work_mode) sp.set('work_mode', params.work_mode)
  if (params.duration?.length) {
    params.duration.forEach((d) => sp.append('duration', String(d)))
  }
  if (params.include_unstated && (params.season?.length || params.duration?.length || params.term)) {
    sp.set('include_unstated', 'true')
  }
  if (params.skills?.length) {
    params.skills.forEach((s) => sp.append('skills', s))
  }
  params.category?.forEach((c) => sp.append('category', c))
  params.company?.forEach((c) => sp.append('company', c))
  if (params.posted_within) sp.set('posted_within', String(params.posted_within))
  if (params.added_since) sp.set('added_since', params.added_since)
  params.country?.forEach((c) => sp.append('country', c))
  if (params.program) sp.set('program', params.program)
  if (params.grad_year) sp.set('grad_year', String(params.grad_year))
  if (params.show_expired) sp.set('show_expired', 'true')
  if (params.show_closed) sp.set('show_closed', 'true')
  if (params.students_only) sp.set('students_only', 'true')
  if (params.hide_senior) sp.set('hide_senior', 'true')
  if (params.search_mode && params.search_mode !== 'keyword') sp.set('search_mode', params.search_mode)
  if (params.sort) sp.set('sort', params.sort)
  if (params.order) sp.set('order', params.order)
  if (params.page && params.page !== 1) sp.set('page', String(params.page))
  if (params.page_size && params.page_size !== 25) sp.set('page_size', String(params.page_size))

  const qs = sp.toString()
  return qs ? `?${qs}` : ''
}

/**
 * The RSS feed address for a search. Same filters as the list, always the newest jobs first,
 * so a feed reader or a feed to email service picks up new jobs on its own
 */
export function feedUrl(params: PostingListParams, origin: string = window.location.origin): string {
  const filters = { ...params, sort: undefined, order: undefined, page: undefined, page_size: undefined }
  const base = API_BASE || origin
  return `${base}/api/postings/feed.rss${buildQueryString(filters)}`
}

const fetchPostings = (params: PostingListParams) =>
  apiFetch<PostingsPage>(`/api/postings${buildQueryString(params)}`)

const fetchPosting = (id: string) => apiFetch<PostingDetail>(`/api/postings/${id}`)

const fetchSimilar = (postingId: string) =>
  apiFetch<SimilarPostingsResponse>(`/api/postings/${postingId}/similar`)

const fetchFilterMeta = () => apiFetch<FilterMeta>('/api/postings/meta/filters')

// The last snapshot this browser saw, so a returning visitor sees jobs before any reply comes back
const SNAPSHOT_STORAGE_KEY = 'coopradar:snapshot'

function readSavedSnapshot(): { data: PostingsSnapshot; savedAt: number } | undefined {
  try {
    const raw = localStorage.getItem(SNAPSHOT_STORAGE_KEY)
    if (!raw) return undefined
    const saved = JSON.parse(raw) as { data?: PostingsSnapshot; savedAt?: number }
    if (!saved.data?.postings?.items || !saved.data.filters) return undefined
    return { data: saved.data, savedAt: saved.savedAt ?? 0 }
  } catch {
    return undefined  // private windows and blocked storage just skip this
  }
}

async function fetchSnapshot(): Promise<PostingsSnapshot> {
  const data = await apiFetch<PostingsSnapshot>('/api/postings/snapshot')
  try {
    localStorage.setItem(SNAPSHOT_STORAGE_KEY, JSON.stringify({ data, savedAt: Date.now() }))
  } catch {
    // Full or blocked storage. The site works the same, only the next visit waits a little
  }
  return data
}

// Adding jobs with a CSV or by hand

export interface RowError {
  row: number      // spreadsheet line number where the header is line 1
  column: string
  message: string
}

export interface CsvUploadResult {
  added: number
  skipped_duplicates: number
  errors: RowError[]
}

export interface ManualPostingIn {
  title: string
  company: string
  city: string
  term: string
  deadline: string          // YYYY-MM-DD
  province?: string
  work_mode?: WorkMode
  duration_months?: number
  description?: string
  skills?: string[]
  source_url?: string
}

/** Upload a CSV of jobs. Up to 1,000 rows and 3 uploads an hour. */
export function useUploadCsv() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (file: File) => {
      const form = new FormData()
      form.append('file', file)
      return apiFetch<CsvUploadResult>('/api/postings/upload', { method: 'POST', body: form })
    },
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['postings'] })
      void qc.invalidateQueries({ queryKey: ['filterMeta'] })
    },
  })
}

/** Add one job by hand. Fails with code DUPLICATE when almost the same job is already there. */
export function useCreatePosting() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (data: ManualPostingIn) =>
      apiFetch<PostingListItem>('/api/postings', { method: 'POST', json: data }),
    onSuccess: () => {
      void qc.invalidateQueries({ queryKey: ['postings'] })
      void qc.invalidateQueries({ queryKey: ['filterMeta'] })
    },
  })
}

// Hooks

/**
 * The jobs page before any filter, ready at once. It starts from the copy saved in this browser,
 * then asks /api/postings/snapshot, which the CDN answers right away even while a free server
 * sleeps. The page shows it while the real list loads, so nobody stares at an empty page.
 */
export function useSnapshot(enabled = true) {
  const qc = useQueryClient()
  const snapshot = useQuery({
    queryKey: ['snapshot'],
    queryFn: fetchSnapshot,
    enabled,
    // Functions so the saved copy is only read once, when the query starts
    initialData: () => readSavedSnapshot()?.data,
    initialDataUpdatedAt: () => readSavedSnapshot()?.savedAt,
    staleTime: 60_000,
    retry: 0,  // it is only a head start, the real list has its own retries
  })

  // The first job's details come in the snapshot too, so the details pane fills right away.
  // Dated like the snapshot, so an old saved copy still gets checked with the server
  const first = snapshot.data?.first_job
  useEffect(() => {
    if (first && !qc.getQueryData(['posting', first.id])) {
      qc.setQueryData(['posting', first.id], first, { updatedAt: snapshot.dataUpdatedAt })
    }
  }, [first, qc, snapshot.dataUpdatedAt])

  return snapshot
}

/**
 * One filtered and sorted page of jobs.
 * The old page stays on screen while the next one loads. `placeholder` is shown before
 * the first reply, like the snapshot for the unfiltered view.
 */
export function usePostings(
  params: PostingListParams,
  options: { enabled?: boolean; placeholder?: PostingsPage } = {},
) {
  return useQuery({
    queryKey: ['postings', params],
    queryFn: () => fetchPostings(params),
    enabled: options.enabled ?? true,
    placeholderData: (prev) => prev ?? options.placeholder,   // keep the last page showing while loading
  })
}

/** One job by id for the details. */
export function usePosting(id: string | undefined) {
  return useQuery({
    queryKey: ['posting', id],
    queryFn: () => fetchPosting(id!),
    enabled: !!id,
  })
}

/** Up to 5 jobs like this one. */
export function useSimilarPostings(postingId: string | undefined) {
  return useQuery({
    queryKey: ['similar', postingId],
    queryFn: () => fetchSimilar(postingId!),
    enabled: !!postingId,
    staleTime: 5 * 60 * 1000,
  })
}

/**
 * The choices for the filters like cities, provinces, terms and skills.
 * Kept for 5 minutes since they only change when new jobs come in.
 */
export function useFilterMeta(placeholder?: FilterMeta) {
  return useQuery({
    queryKey: ['filterMeta'],
    queryFn: fetchFilterMeta,
    staleTime: 5 * 60 * 1000,
    placeholderData: placeholder,
  })
}
