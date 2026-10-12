/**
 * PostingsListPage: the jobs page. Owns all URL state.
 *
 * Every filter, search query, sort, order, page, page_size, view and show_expired
 * value lives in the URL query string via useSearchParams. This means:
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
import {
  useFilterMeta, usePostings,
  type CategoryKey, type PageSize, type SearchMode, type SortField, type SortOrder, type WorkMode,
} from '../api/postings'
import { useMe } from '../api/auth'
import { usePublicConfig } from '../api/meta'
import { useMatches } from '../api/resume'
import FilterBar, { ActiveFilterChips } from '../components/FilterBar'
import type { Filters, Level } from '../components/filters'
import { ArrowRightIcon, GridIcon, ListIcon } from '../components/Icons'
import PostingsTable from '../components/PostingsTable'
import SearchBox from '../components/SearchBox'
import { SearchModeToggle } from '../components/SearchModeToggle'
import WelcomeHero from '../components/WelcomeHero'

// URL param names: keep in one place so there's no typo drift
const P = {
  q: 'q', city: 'city', province: 'province', term: 'term',
  work_mode: 'work_mode', duration: 'duration', skills: 'skills',
  category: 'category', company: 'company', posted_within: 'posted_within',
  show_expired: 'show_expired', search_mode: 'search_mode', level: 'level',
  sort: 'sort', order: 'order', view: 'view',
  page: 'page', page_size: 'page_size',
} as const

const PAGE_SIZES: PageSize[] = [10, 25, 50]
const CATEGORY_KEYS: CategoryKey[] = [
  'software', 'data', 'design', 'product', 'hardware', 'it_security', 'business',
  'sales_marketing', 'customer',
]

// One dropdown for sort field + direction, like most job boards
const SORTS: { value: string; label: string; sort: SortField; order: SortOrder }[] = [
  { value: 'posted_at:desc', label: 'Newest first', sort: 'posted_at', order: 'desc' },
  { value: 'deadline:asc', label: 'Deadline soonest', sort: 'deadline', order: 'asc' },
  { value: 'company:asc', label: 'Company A to Z', sort: 'company', order: 'asc' },
  { value: 'title:asc', label: 'Job title A to Z', sort: 'title', order: 'asc' },
  { value: 'posted_at:asc', label: 'Oldest first', sort: 'posted_at', order: 'asc' },
]

export default function PostingsListPage() {
  const [sp, setSp] = useSearchParams()
  const { data: me, isLoading: meLoading } = useMe()
  const { data: config } = usePublicConfig()
  const { data: matches } = useMatches(Boolean(me))
  const hasResume = Boolean(matches?.resume)

  // --- Read params from URL (with sensible defaults) -------------------------
  const q            = sp.get(P.q) ?? ''
  const city         = sp.get(P.city) ?? ''
  const province     = sp.get(P.province) ?? ''
  const term         = sp.get(P.term) ?? ''
  const work_mode    = (sp.get(P.work_mode) ?? '') as WorkMode | ''
  const duration     = sp.getAll(P.duration).map(Number).filter((d) => [4, 8, 12, 16].includes(d))
  const skills       = sp.getAll(P.skills).filter(Boolean)
  const category     = sp.getAll(P.category).filter((c): c is CategoryKey => CATEGORY_KEYS.includes(c as CategoryKey))
  const company      = sp.getAll(P.company).filter(Boolean)
  const posted_raw   = Number(sp.get(P.posted_within))
  const posted_within = [1, 3, 7, 14, 30].includes(posted_raw) ? posted_raw : 0
  const show_expired = sp.get(P.show_expired) === 'true'
  // Level: '' = students & entry-level (default, hides senior roles) · 'students' · 'all'
  const level = (sp.get(P.level) ?? (sp.get('students_only') === 'true' ? 'students' : '')) as Level
  const students_only = level === 'students'
  const hide_senior = level === ''
  const search_mode  = ((sp.get(P.search_mode) ?? 'keyword') as SearchMode)
  const sort         = (sp.get(P.sort) ?? 'posted_at') as SortField
  const order        = (sp.get(P.order) ?? 'desc') as SortOrder
  const view         = sp.get(P.view) === 'table' ? 'table' : 'cards'
  const page         = Math.max(1, Number(sp.get(P.page) ?? 1))
  const page_size    = (([10, 25, 50].includes(Number(sp.get(P.page_size))) ? Number(sp.get(P.page_size)) : 25)) as PageSize

  const filters: Filters = {
    category, level, province, city, work_mode, posted_within, term, duration, company, skills,
    show_expired,
  }

  // --- Fetch data ------------------------------------------------------------
  const { data, isLoading, isError, refetch } = usePostings({
    q: q || undefined,
    city: city || undefined,
    province: province || undefined,
    term: term || undefined,
    work_mode: work_mode || undefined,
    duration: duration.length ? duration : undefined,
    skills: skills.length ? skills : undefined,
    category: category.length ? category : undefined,
    company: company.length ? company : undefined,
    posted_within: posted_within || undefined,
    show_expired,
    students_only,
    hide_senior,
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
      // Reset to page 1 whenever a filter/sort changes: the old page may not exist
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

  function changeFilters(patch: Partial<Filters>) {
    const url: Record<string, string | string[] | null> = {}
    if ('category' in patch) url[P.category] = patch.category ?? null
    if ('level' in patch) { url[P.level] = patch.level || null; url.students_only = null }
    if ('province' in patch) url[P.province] = patch.province || null
    if ('city' in patch) url[P.city] = patch.city || null
    if ('work_mode' in patch) url[P.work_mode] = patch.work_mode || null
    if ('posted_within' in patch) url[P.posted_within] = patch.posted_within ? String(patch.posted_within) : null
    if ('term' in patch) url[P.term] = patch.term || null
    if ('duration' in patch) url[P.duration] = patch.duration?.map(String) ?? null
    if ('company' in patch) url[P.company] = patch.company ?? null
    if ('skills' in patch) url[P.skills] = patch.skills ?? null
    if ('show_expired' in patch) url[P.show_expired] = patch.show_expired ? 'true' : null
    update(url)
  }

  function clearAll() {
    // Keep the search text and layout; drop every filter
    const next = new URLSearchParams()
    if (q) next.set(P.q, q)
    if (view === 'table') next.set(P.view, 'table')
    setSp(next, { replace: true })
  }

  const totalPages = data ? Math.max(1, Math.ceil(data.total / page_size)) : 1
  const sortValue = `${sort}:${order}`

  return (
    <div className="mx-auto max-w-7xl space-y-6 px-4 py-6 sm:py-8">
      {/* Introduction for visitors who haven't matched a resume yet */}
      {!meLoading && !hasResume && (
        <WelcomeHero
          jobs={meta?.open_jobs}
          employers={meta?.companies?.length}
        />
      )}

      {/* Signed-in with a resume: a shortcut back to the matches */}
      {hasResume && (
        <Link
          to="/resume"
          className="flex items-center justify-between gap-3 rounded-lg border border-blue-200 bg-blue-50 px-4 py-3 text-sm text-blue-900 hover:bg-blue-100"
        >
          <span>
            <span className="font-semibold">{matches?.items.length ?? 0} jobs match your resume.</span>{' '}
            See them ranked, with the skills each one wants.
          </span>
          <ArrowRightIcon className="h-4 w-4 shrink-0" />
        </Link>
      )}

      <div>
        <h1 className="text-2xl font-bold tracking-tight text-gray-900">Browse jobs</h1>
        <p className="mt-1 text-sm text-gray-600">
          Co-op, intern and entry-level roles from employers' own career pages, refreshed every few hours.
        </p>
      </div>

      {/* Search */}
      <div className="flex flex-wrap items-center gap-3">
        <div className="min-w-0 flex-1">
          <SearchBox value={q} onSearch={(v) => update({ [P.q]: v || null })} />
        </div>
        {config?.semantic_search_enabled && (
          <SearchModeToggle
            value={search_mode}
            onChange={(mode) => update({ [P.search_mode]: mode === 'keyword' ? null : mode })}
          />
        )}
      </div>

      <div className="grid gap-6 lg:grid-cols-[17rem_1fr]">
        <FilterBar
          filters={filters}
          meta={meta}
          metaLoading={metaLoading}
          onChange={changeFilters}
          onClearAll={clearAll}
        />

        <div className="min-w-0 space-y-4">
          {/* Result count, sort, layout */}
          <div className="flex flex-wrap items-center justify-between gap-3">
            <p className="text-sm text-gray-700" aria-live="polite" aria-atomic="true">
              {data ? (
                <><span className="font-semibold text-gray-900">{data.total.toLocaleString()}</span> job{data.total !== 1 ? 's' : ''}</>
              ) : 'Loading jobs...'}
            </p>
            <div className="flex items-center gap-2">
              <label htmlFor="sort-select" className="text-sm text-gray-600">Sort</label>
              <select
                id="sort-select"
                value={SORTS.some((s) => s.value === sortValue) ? sortValue : 'posted_at:desc'}
                onChange={(e) => {
                  const s = SORTS.find((x) => x.value === e.target.value)
                  if (s) update({ [P.sort]: s.sort, [P.order]: s.order })
                }}
                className="rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-sm focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
              >
                {SORTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
              </select>
              <div className="hidden md:inline-flex overflow-hidden rounded-md border border-gray-300 bg-white" role="group" aria-label="Layout">
                <ViewButton active={view === 'cards'} label="Cards" onClick={() => update({ [P.view]: null })}>
                  <GridIcon className="h-4 w-4" />
                </ViewButton>
                <ViewButton active={view === 'table'} label="Table" onClick={() => update({ [P.view]: 'table' })}>
                  <ListIcon className="h-4 w-4" />
                </ViewButton>
              </div>
            </div>
          </div>

          <ActiveFilterChips filters={filters} meta={meta} onChange={changeFilters} onClearAll={clearAll} />

          <PostingsTable
            data={data?.items ?? []}
            isLoading={isLoading}
            isError={isError}
            onRetry={() => refetch()}
            sort={sort}
            order={order}
            onSortChange={(field, dir) => update({ [P.sort]: field, [P.order]: dir })}
            showBookmarks
            onClearFilters={clearAll}
            view={view}
          />

          {data && data.total === 0 && students_only && (
            <p className="text-sm text-gray-600">
              Few co-op and intern roles are open right now. Most are posted in waves before each term.{' '}
              <button type="button" className="font-medium text-blue-700 hover:underline" onClick={() => changeFilters({ level: '' })}>
                Show entry-level jobs too
              </button>
              , since many junior roles welcome students.
            </p>
          )}

          {/* Pagination */}
          {data && data.total > 0 && (
            <nav className="flex flex-col items-center justify-between gap-4 pt-2 sm:flex-row" aria-label="Pages">
              <div className="flex items-center gap-2 text-sm text-gray-600">
                <label htmlFor="page-size-select">Per page</label>
                <select
                  id="page-size-select"
                  value={page_size}
                  onChange={(e) => update({ [P.page_size]: e.target.value, [P.page]: '1' })}
                  className="rounded-md border border-gray-300 bg-white px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-600"
                >
                  {PAGE_SIZES.map((s) => <option key={s} value={s}>{s}</option>)}
                </select>
              </div>

              <div className="flex items-center gap-2 text-sm">
                <button
                  disabled={page <= 1}
                  onClick={() => update({ [P.page]: String(page - 1) })}
                  className="rounded-md border border-gray-300 bg-white px-3 py-1.5 hover:bg-gray-50 disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-blue-600"
                  aria-label="Previous page"
                >
                  Previous
                </button>
                <span className="px-2 text-gray-600">Page {page} of {totalPages}</span>
                <button
                  disabled={page >= totalPages}
                  onClick={() => update({ [P.page]: String(page + 1) })}
                  className="rounded-md border border-gray-300 bg-white px-3 py-1.5 hover:bg-gray-50 disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-blue-600"
                  aria-label="Next page"
                >
                  Next
                </button>
              </div>
            </nav>
          )}
          <p className="text-xs text-gray-500">
            Know a job that's missing? Signed-in users can <Link to="/add" className="underline">add it</Link>.
          </p>
        </div>
      </div>
    </div>
  )
}

function ViewButton({
  active, label, onClick, children,
}: { active: boolean; label: string; onClick: () => void; children: React.ReactNode }) {
  return (
    <button
      type="button"
      onClick={onClick}
      aria-pressed={active}
      title={label}
      className={`flex items-center gap-1.5 px-2.5 py-1.5 text-sm ${active ? 'bg-gray-100 text-gray-900' : 'text-gray-500 hover:text-gray-800'}`}
    >
      {children}
      <span className="sr-only lg:not-sr-only">{label}</span>
    </button>
  )
}
