/**
 * PostingsListPage — owns all URL state.
 *
 * Every filter, search query, sort, order, page, page_size, and show_expired
 * value lives in the URL query string via useSearchParams.  This means:
 *  - Views are shareable by copying the URL
 *  - Navigating to the detail page and pressing Back restores the exact state
 *  - Refreshing the page doesn't reset anything
 *
 * CHK013 decision: all URL params are read before the first usePostings call
 * because the hook is inside the component body (after the params are parsed).
 * CHK017 decision: each filter change replaces the current history entry
 * (replace: true) so the back button goes back to wherever the user came from,
 * not through every filter change.
 */

import { useCallback } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import { useFilterMeta, usePostings, type SearchMode, type SortField, type SortOrder, type WorkMode, type PageSize } from '../api/postings'
import { useMe } from '../api/auth'
import { usePublicConfig } from '../api/meta'
import FilterBar from '../components/FilterBar'
import PostingsTable from '../components/PostingsTable'
import SearchBox from '../components/SearchBox'
import { SearchModeToggle } from '../components/SearchModeToggle'
import WelcomeHero from '../components/WelcomeHero'

// URL param names — keep in one place so there's no typo drift
const P = {
  q: 'q', city: 'city', province: 'province', term: 'term',
  work_mode: 'work_mode', duration: 'duration', skills: 'skills',
  show_expired: 'show_expired', search_mode: 'search_mode', students_only: 'students_only',
  sort: 'sort', order: 'order',
  page: 'page', page_size: 'page_size',
} as const

const PAGE_SIZES: PageSize[] = [10, 25, 50]

export default function PostingsListPage() {
  const [sp, setSp] = useSearchParams()
  const { data: me, isLoading: meLoading } = useMe()
  const { data: config } = usePublicConfig()

  // --- Read params from URL (with sensible defaults) -------------------------
  const q            = sp.get(P.q) ?? ''
  const city         = sp.get(P.city) ?? ''
  const province     = sp.get(P.province) ?? ''
  const term         = sp.get(P.term) ?? ''
  const work_mode    = (sp.get(P.work_mode) ?? '') as WorkMode | ''
  const duration     = sp.getAll(P.duration).map(Number).filter((d) => [4,8,12,16].includes(d))
  const skills       = sp.getAll(P.skills).filter(Boolean)
  const show_expired = sp.get(P.show_expired) === 'true'
  const students_only = sp.get(P.students_only) === 'true'
  const search_mode  = ((sp.get(P.search_mode) ?? 'keyword') as SearchMode)
  const sort         = (sp.get(P.sort) ?? 'posted_at') as SortField
  const order        = (sp.get(P.order) ?? 'desc') as SortOrder
  const page         = Math.max(1, Number(sp.get(P.page) ?? 1))
  const page_size    = (([10, 25, 50].includes(Number(sp.get(P.page_size))) ? Number(sp.get(P.page_size)) : 25)) as PageSize

  // --- Fetch data ------------------------------------------------------------
  const { data, isLoading, isError, refetch } = usePostings({
    q: q || undefined,
    city: city || undefined,
    province: province || undefined,
    term: term || undefined,
    work_mode: work_mode || undefined,
    duration: duration.length ? duration : undefined,
    skills: skills.length ? skills : undefined,
    show_expired,
    students_only,
    search_mode,
    sort,
    order,
    page,
    page_size,
  })

  const { data: meta, isLoading: metaLoading } = useFilterMeta()

  // --- URL update helpers ---------------------------------------------------
  // All changes replace the current history entry so Back works naturally
  const update = useCallback((patches: Record<string, string | string[] | null>) => {
    setSp((prev) => {
      const next = new URLSearchParams(prev)
      // Reset to page 1 whenever a filter/sort changes — old page may not exist
      next.set(P.page, '1')
      for (const [key, val] of Object.entries(patches)) {
        if (val === null || val === '' || (Array.isArray(val) && val.length === 0)) {
          next.delete(key)
        } else if (Array.isArray(val)) {
          next.delete(key)
          val.forEach((v) => next.append(key, v))
        } else {
          next.set(key, val)
        }
      }
      return next
    }, { replace: true })
  }, [setSp])

  function clearAll() {
    setSp(new URLSearchParams(), { replace: true })
  }

  return (
    <div className="max-w-7xl mx-auto px-4 py-8 space-y-6">
      {/* First-visit introduction for signed-out visitors */}
      {!meLoading && !me && <WelcomeHero />}

      {/* Header */}
      <div className="flex flex-wrap items-end justify-between gap-3">
        <div>
          <h1 className="text-2xl font-bold text-gray-900">Jobs</h1>
          <p className="text-sm text-gray-500 mt-0.5">
            {data ? `${data.total} open job${data.total !== 1 ? 's' : ''}` : 'Loading…'} · pulled from
            employers' own career pages and refreshed every few hours
          </p>
        </div>

        <div className="flex flex-wrap items-center gap-4">
        {/* Students-only toggle */}
        <label className="flex items-center gap-2 text-sm font-medium text-gray-800 cursor-pointer select-none">
          <input
            type="checkbox"
            className="rounded border-gray-300 text-brand-500 focus:ring-brand-500"
            checked={students_only}
            onChange={(e) => update({ [P.students_only]: e.target.checked ? 'true' : null })}
          />
          Co-op &amp; intern roles only
        </label>

        {/* Show expired toggle */}
        <label className="flex items-center gap-2 text-sm text-gray-600 cursor-pointer select-none">
          <input
            type="checkbox"
            className="rounded border-gray-300 text-brand-500 focus:ring-brand-500"
            checked={show_expired}
            onChange={(e) => update({ [P.show_expired]: e.target.checked ? 'true' : null })}
          />
          Show expired
        </label>
        </div>
      </div>

      {/* Search */}
      <div className="flex items-center gap-3 flex-wrap">
        <div className="flex-1 min-w-0">
          <SearchBox
            value={q}
            onSearch={(v) => update({ [P.q]: v || null })}
          />
        </div>
        {config?.semantic_search_enabled && (
          <SearchModeToggle
            value={search_mode}
            onChange={(mode) => update({ [P.search_mode]: mode === 'keyword' ? null : mode })}
          />
        )}
      </div>

      {/* Filters */}
      <FilterBar
        filters={{ city, province, term, work_mode, duration, skills }}
        meta={meta}
        metaLoading={metaLoading}
        onChange={(patches) => {
          const urlPatches: Record<string, string | string[] | null> = {}
          if ('city' in patches) urlPatches[P.city] = patches.city ?? null
          if ('province' in patches) urlPatches[P.province] = patches.province ?? null
          if ('term' in patches) urlPatches[P.term] = patches.term ?? null
          if ('work_mode' in patches) urlPatches[P.work_mode] = patches.work_mode ?? null
          if ('duration' in patches) urlPatches[P.duration] = patches.duration?.map(String) ?? null
          if ('skills' in patches) urlPatches[P.skills] = patches.skills ?? null
          update(urlPatches)
        }}
        onClearAll={clearAll}
      />

      {/* Table */}
      <PostingsTable
        data={data?.items ?? []}
        isLoading={isLoading}
        isError={isError}
        onRetry={() => refetch()}
        sort={sort}
        order={order}
        onSortChange={(field, dir) => update({ [P.sort]: field, [P.order]: dir })}
      />

      {data && data.total === 0 && students_only && (
        <p className="text-sm text-gray-600">
          No co-op or intern roles match right now — most are posted in waves before each term.{' '}
          <button type="button" className="text-blue-700 hover:underline" onClick={() => update({ [P.students_only]: null })}>
            Show all jobs
          </button>{' '}
          (many junior roles welcome students too).
        </p>
      )}

      {/* Pagination */}
      {data && data.total > 0 && (
        <div className="flex flex-col sm:flex-row items-center justify-between gap-4">
          {/* Page size selector */}
          <div className="flex items-center gap-2 text-sm text-gray-600">
            <label htmlFor="page-size-select">Rows per page:</label>
            <select
              id="page-size-select"
              value={page_size}
              onChange={(e) => update({ [P.page_size]: e.target.value, [P.page]: '1' })}
              className="border border-gray-300 rounded px-2 py-1 text-sm focus:outline-none focus:ring-2 focus:ring-brand-500"
            >
              {PAGE_SIZES.map((s) => (
                <option key={s} value={s}>{s}</option>
              ))}
            </select>
          </div>

          {/* Page navigation */}
          <div className="flex items-center gap-3 text-sm">
            <span className="text-gray-500">
              Page {page} of {Math.max(1, Math.ceil(data.total / page_size))}
            </span>
            <button
              disabled={page <= 1}
              onClick={() => update({ [P.page]: String(page - 1) })}
              className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-40 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
              aria-label="Previous page"
            >
              ← Prev
            </button>
            <button
              disabled={page >= Math.ceil(data.total / page_size)}
              onClick={() => update({ [P.page]: String(page + 1) })}
              className="px-3 py-1 border border-gray-300 rounded text-sm disabled:opacity-40 hover:bg-gray-50 focus:outline-none focus:ring-2 focus:ring-brand-500"
              aria-label="Next page"
            >
              Next →
            </button>
          </div>
        </div>
      )}
      <p className="text-xs text-gray-400">
        Know a posting that's missing? Signed-in users can <Link to="/add" className="underline">add postings</Link>.
      </p>
    </div>
  )
}
