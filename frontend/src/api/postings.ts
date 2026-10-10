/**
 * TanStack Query hooks for the postings API.
 *
 * All API types are inlined here until `npm run gen:api` generates types.gen.ts
 * from the FastAPI OpenAPI schema. Once generated, import from './types.gen.ts'.
 */

import { useQuery } from '@tanstack/react-query'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

// ── Types ─────────────────────────────────────────────────────────────────────

export type WorkMode = 'onsite' | 'hybrid' | 'remote'

export interface PostingListItem {
  id: string
  title: string
  company: string
  city: string
  province: string
  work_mode: WorkMode
  term: string
  duration_months: number
  deadline: string          // ISO date string "YYYY-MM-DD"
  posted_at: string         // ISO datetime string
  skills: string[]
  source_url: string | null
  closed_at: string | null
  is_closed: boolean        // derived: closed_at !== null
  // Populated for authenticated requests; null/undefined for unauthenticated
  is_saved?: boolean | null
}

export interface PostingDetail extends PostingListItem {
  description: string
  low_confidence_fields?: Record<string, number> | null
}

export interface SimilarPostingOut {
  id: string
  title: string
  company: string
  city: string
  province: string
  work_mode: WorkMode | null
  term: string
  deadline: string | null
  similarity: number
}

export interface SimilarPostingsResponse {
  items: SimilarPostingOut[]
}

export type SearchMode = 'keyword' | 'semantic'

export interface PostingsPage {
  items: PostingListItem[]
  total: number
  page: number
  page_size: number
}

export interface FilterMeta {
  cities: string[]
  provinces: string[]
  terms: string[]
  skills: string[]
}

export type SortField = 'posted_at' | 'deadline' | 'company' | 'title'
export type SortOrder = 'asc' | 'desc'
export type PageSize = 10 | 25 | 50

export interface PostingListParams {
  q?: string
  city?: string
  province?: string
  term?: string
  work_mode?: WorkMode
  duration?: number[]
  skills?: string[]
  show_expired?: boolean
  show_closed?: boolean
  search_mode?: SearchMode
  sort?: SortField
  order?: SortOrder
  page?: number
  page_size?: PageSize
}

// ── Fetcher ───────────────────────────────────────────────────────────────────

function buildQueryString(params: PostingListParams): string {
  const sp = new URLSearchParams()

  if (params.q) sp.set('q', params.q)
  if (params.city) sp.set('city', params.city)
  if (params.province) sp.set('province', params.province)
  if (params.term) sp.set('term', params.term)
  if (params.work_mode) sp.set('work_mode', params.work_mode)
  if (params.duration?.length) {
    params.duration.forEach((d) => sp.append('duration', String(d)))
  }
  if (params.skills?.length) {
    params.skills.forEach((s) => sp.append('skills', s))
  }
  if (params.show_expired) sp.set('show_expired', 'true')
  if (params.show_closed) sp.set('show_closed', 'true')
  if (params.search_mode && params.search_mode !== 'keyword') sp.set('search_mode', params.search_mode)
  if (params.sort) sp.set('sort', params.sort)
  if (params.order) sp.set('order', params.order)
  if (params.page && params.page !== 1) sp.set('page', String(params.page))
  if (params.page_size && params.page_size !== 25) sp.set('page_size', String(params.page_size))

  const qs = sp.toString()
  return qs ? `?${qs}` : ''
}

async function fetchPostings(params: PostingListParams): Promise<PostingsPage> {
  const res = await fetch(`${API_BASE}/api/postings${buildQueryString(params)}`)
  if (!res.ok) throw new Error(`GET /api/postings failed: ${res.status}`)
  return res.json() as Promise<PostingsPage>
}

async function fetchPosting(id: string): Promise<PostingDetail> {
  const res = await fetch(`${API_BASE}/api/postings/${id}`)
  if (res.status === 404) throw new Error('Posting not found')
  if (!res.ok) throw new Error(`GET /api/postings/${id} failed: ${res.status}`)
  return res.json() as Promise<PostingDetail>
}

async function fetchSimilar(postingId: string): Promise<SimilarPostingsResponse> {
  const res = await fetch(`${API_BASE}/api/postings/${postingId}/similar`)
  if (!res.ok) throw new Error(`GET /api/postings/${postingId}/similar failed: ${res.status}`)
  return res.json() as Promise<SimilarPostingsResponse>
}

async function fetchFilterMeta(): Promise<FilterMeta> {
  const res = await fetch(`${API_BASE}/api/postings/meta/filters`)
  if (!res.ok) throw new Error(`GET /api/postings/meta/filters failed: ${res.status}`)
  return res.json() as Promise<FilterMeta>
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

/**
 * Fetch a paginated, filtered, sorted list of postings.
 * keepPreviousData ensures the old page stays visible while the next loads.
 */
export function usePostings(params: PostingListParams) {
  return useQuery({
    queryKey: ['postings', params],
    queryFn: () => fetchPostings(params),
    placeholderData: (prev) => prev,   // keeps previous page visible during fetch
  })
}

/** Fetch a single posting by ID for the detail page. */
export function usePosting(id: string | undefined) {
  return useQuery({
    queryKey: ['posting', id],
    queryFn: () => fetchPosting(id!),
    enabled: !!id,
  })
}

/** Fetch up to 5 similar postings for a given posting ID. */
export function useSimilarPostings(postingId: string | undefined) {
  return useQuery({
    queryKey: ['similar', postingId],
    queryFn: () => fetchSimilar(postingId!),
    enabled: !!postingId,
    staleTime: 5 * 60 * 1000,
  })
}

/**
 * Fetch filter metadata (cities, provinces, terms, skills).
 * Stale for 5 minutes — values only change when postings are ingested.
 */
export function useFilterMeta() {
  return useQuery({
    queryKey: ['filterMeta'],
    queryFn: fetchFilterMeta,
    staleTime: 5 * 60 * 1000,
  })
}
