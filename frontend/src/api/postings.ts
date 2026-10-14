/**
 * TanStack Query hooks for the postings API.
 *
 * Types mirror the backend Pydantic schemas (app/schemas/posting.py). To regenerate
 * them from the live OpenAPI schema run `npm run gen:api` (writes src/api/types.gen.ts).
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { apiFetch } from './client'
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
  | 'posted_at' | 'deadline' | 'company' | 'title' | 'duration_months' | 'term_start'
export type SortOrder = 'asc' | 'desc'
export type PageSize = 10 | 25 | 50

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
  if (params.skills?.length) {
    params.skills.forEach((s) => sp.append('skills', s))
  }
  params.category?.forEach((c) => sp.append('category', c))
  params.company?.forEach((c) => sp.append('company', c))
  if (params.posted_within) sp.set('posted_within', String(params.posted_within))
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

const fetchPostings = (params: PostingListParams) =>
  apiFetch<PostingsPage>(`/api/postings${buildQueryString(params)}`)

const fetchPosting = (id: string) => apiFetch<PostingDetail>(`/api/postings/${id}`)

const fetchSimilar = (postingId: string) =>
  apiFetch<SimilarPostingsResponse>(`/api/postings/${postingId}/similar`)

const fetchFilterMeta = () => apiFetch<FilterMeta>('/api/postings/meta/filters')

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
 * One filtered and sorted page of jobs.
 * The old page stays on screen while the next one loads.
 */
export function usePostings(params: PostingListParams) {
  return useQuery({
    queryKey: ['postings', params],
    queryFn: () => fetchPostings(params),
    placeholderData: (prev) => prev,   // keep the last page showing while loading
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
export function useFilterMeta() {
  return useQuery({
    queryKey: ['filterMeta'],
    queryFn: fetchFilterMeta,
    staleTime: 5 * 60 * 1000,
  })
}
