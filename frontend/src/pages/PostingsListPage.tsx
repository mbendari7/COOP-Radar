/**
 * PostingsListPage: the jobs page, laid out like a job board.
 *
 *   ┌ search band ─ What [job, company, skill]  Where [province/state]  [Find jobs] ┐
 *   │ quick filters: level · work mode · country · All filters (n)                  │
 *   ├ results list (cards) ─────────┬ details of the selected job ──────────────────┤
 *
 * All state lives in the URL query string (useSearchParams), so views are shareable, Back from
 * a job restores the exact list, and refreshing keeps everything. Each change replaces the
 * current history entry so Back leaves the page instead of undoing filters one by one.
 *
 * Defaults are for students: co-op & internships, in Canada. ?level=entry adds entry-level
 * jobs, ?level=all everything; ?country=US or ?country=all adds US student roles.
 */

import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  useFilterMeta, usePostings,
  type CategoryKey, type PageSize, type ProgramKey, type SearchMode, type SortField,
  type SortOrder, type WorkMode,
} from '../api/postings'
import { useMe } from '../api/auth'
import { usePublicConfig } from '../api/meta'
import { useMatches } from '../api/resume'
import DemoButton from '../components/DemoButton'
import { ActiveFilterChips, FilterDrawer, Pill } from '../components/FilterBar'
import {
  COUNTRY_CHOICES, LEVELS, WORK_MODES, countActive, countriesFor,
  type CountryChoice, type Filters, type Level,
} from '../components/filters'
import { ArrowRightIcon, FilterIcon, GridIcon, ListIcon, PinIcon, SearchIcon } from '../components/Icons'
import { PostingDetailPane } from '../components/PostingDetailView'
import PostingsTable from '../components/PostingsTable'
import { SearchModeToggle } from '../components/SearchModeToggle'
import { isProvince, provinceName, workModeLabel } from '../utils/format'

// URL param names: keep in one place so there's no typo drift
const P = {
  q: 'q', city: 'city', province: 'province', term: 'term',
  work_mode: 'work_mode', duration: 'duration', skills: 'skills',
  category: 'category', company: 'company', posted_within: 'posted_within',
  show_expired: 'show_expired', search_mode: 'search_mode', level: 'level',
  country: 'country', program: 'program', grad_year: 'grad_year',
  sort: 'sort', order: 'order', view: 'view', job: 'job',
  page: 'page', page_size: 'page_size',
} as const

const PAGE_SIZES: PageSize[] = [10, 25, 50]
const CATEGORY_KEYS: CategoryKey[] = [
  'software', 'data', 'design', 'product', 'hardware', 'it_security', 'business',
  'sales_marketing', 'customer',
]

// One dropdown for sort field + direction, like most job boards
const SORTS: { value: string; label: string; sort: SortField; order: SortOrder }[] = [
  { value: 'posted_at:desc', label: 'Most recent', sort: 'posted_at', order: 'desc' },
  { value: 'deadline:asc', label: 'Deadline soonest', sort: 'deadline', order: 'asc' },
  { value: 'company:asc', label: 'Company A to Z', sort: 'company', order: 'asc' },
  { value: 'title:asc', label: 'Job title A to Z', sort: 'title', order: 'asc' },
]

function readLevel(sp: URLSearchParams): Level {
  const raw = sp.get(P.level)
  if (raw === 'entry' || raw === 'all') return raw
  return ''  // co-op & internships (older links used level=students for this)
}

function readCountry(sp: URLSearchParams): CountryChoice {
  const raw = sp.get(P.country)
  return raw === 'US' || raw === 'all' ? raw : ''
}

export default function PostingsListPage() {
  const [sp, setSp] = useSearchParams()
  const { data: me, isLoading: meLoading } = useMe()
  const { data: config } = usePublicConfig()
  const { data: matches } = useMatches(Boolean(me))
  const hasResume = Boolean(matches?.resume)
  const [drawerOpen, setDrawerOpen] = useState(false)

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
  const level        = readLevel(sp)
  const country      = readCountry(sp)
  const program      = (sp.get(P.program) ?? '') as ProgramKey | ''
  const grad_raw     = Number(sp.get(P.grad_year))
  const grad_year    = grad_raw >= 2000 && grad_raw <= 2100 ? grad_raw : 0
  const search_mode  = ((sp.get(P.search_mode) ?? 'keyword') as SearchMode)
  const sort         = (sp.get(P.sort) ?? 'posted_at') as SortField
  const order        = (sp.get(P.order) ?? 'desc') as SortOrder
  const view         = sp.get(P.view) === 'table' ? 'table' : 'cards'
  const jobParam     = sp.get(P.job)
  const page         = Math.max(1, Number(sp.get(P.page) ?? 1))
  const page_size    = (([10, 25, 50].includes(Number(sp.get(P.page_size))) ? Number(sp.get(P.page_size)) : 25)) as PageSize

  const filters: Filters = {
    category, level, country, program, grad_year, province, city, work_mode, posted_within,
    term, duration, company, skills, show_expired,
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
    country: countriesFor(country),
    program: program || undefined,
    grad_year: grad_year || undefined,
    show_expired,
    students_only: level === '',
    hide_senior: level === 'entry',
    search_mode,
    sort,
    order,
    page,
    page_size,
  })

  const { data: meta, isLoading: metaLoading } = useFilterMeta()

  // --- URL update helpers ---------------------------------------------------
  const update = useCallback((patches: Record<string, string | string[] | null>) => {
    setSp((prev) => {
      const next = new URLSearchParams(prev)
      // A new filter or sort starts at page 1 with the first result selected
      next.set(P.page, '1')
      next.delete(P.job)
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

  const selectJob = useCallback((id: string) => {
    setSp((prev) => {
      const next = new URLSearchParams(prev)
      next.set(P.job, id)
      return next
    }, { replace: true })
  }, [setSp])

  function changeFilters(patch: Partial<Filters>) {
    const url: Record<string, string | string[] | null> = {}
    if ('category' in patch) url[P.category] = patch.category ?? null
    if ('level' in patch) { url[P.level] = patch.level || null; url.students_only = null }
    if ('country' in patch) url[P.country] = patch.country || null
    if ('program' in patch) url[P.program] = patch.program || null
    if ('grad_year' in patch) url[P.grad_year] = patch.grad_year ? String(patch.grad_year) : null
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

  const clearAll = useCallback(() => {
    // Keep the search text and layout; drop every filter
    const next = new URLSearchParams()
    if (q) next.set(P.q, q)
    if (view === 'table') next.set(P.view, 'table')
    setSp(next, { replace: true })
  }, [q, view, setSp])

  const items = data?.items ?? []
  const selectedId = jobParam ?? items[0]?.id ?? null
  const totalPages = data ? Math.max(1, Math.ceil(data.total / page_size)) : 1
  const sortValue = `${sort}:${order}`
  const active = countActive(filters)

  return (
    <div>
      {/* ── Search band ─────────────────────────────────────────────────── */}
      <div className="border-b border-gray-200 bg-white">
        <div className="mx-auto max-w-7xl px-4 py-5">
          <JobSearchForm
            q={q}
            province={province}
            country={country}
            provinces={meta?.provinces ?? []}
            onSearch={(what, where) => update({ [P.q]: what || null, [P.province]: where || null, [P.city]: null })}
          />

          {/* Quick filters: the ones people change most, one tap each */}
          <div className="-mx-4 mt-4 flex items-center gap-2 overflow-x-auto px-4 pb-1" role="group" aria-label="Quick filters">
            <select
              aria-label="Experience level"
              value={level}
              onChange={(e) => changeFilters({ level: e.target.value as Level })}
              className="shrink-0 rounded-full border border-gray-400 bg-white py-1 pl-3 pr-8 text-sm font-medium text-gray-800 hover:border-gray-600 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
            >
              {LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
            </select>
            <select
              aria-label="Country"
              value={country}
              onChange={(e) => changeFilters({ country: e.target.value as CountryChoice, province: '', city: '' })}
              className="shrink-0 rounded-full border border-gray-400 bg-white py-1 pl-3 pr-8 text-sm font-medium text-gray-800 hover:border-gray-600 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
            >
              {COUNTRY_CHOICES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
            <span className="mx-1 h-5 w-px shrink-0 bg-gray-300" aria-hidden="true" />
            {WORK_MODES.map((m) => (
              <span key={m} className="shrink-0">
                <Pill
                  on={work_mode === m}
                  onClick={() => changeFilters({ work_mode: work_mode === m ? '' : m })}
                >
                  {workModeLabel(m)}
                </Pill>
              </span>
            ))}
            <span className="mx-1 h-5 w-px shrink-0 bg-gray-300" aria-hidden="true" />
            <button
              type="button"
              onClick={() => setDrawerOpen(true)}
              className="inline-flex shrink-0 items-center gap-1.5 rounded-full border border-gray-400 bg-white px-3 py-1 text-sm font-medium text-gray-800 hover:border-gray-600 hover:bg-gray-50"
            >
              <FilterIcon className="h-4 w-4" />
              All filters
              {active > 0 && (
                <span className="rounded-full bg-blue-600 px-1.5 text-xs font-semibold text-white">{active}</span>
              )}
            </button>
            {config?.semantic_search_enabled && (
              <span className="ml-auto shrink-0">
                <SearchModeToggle
                  value={search_mode}
                  onChange={(mode) => update({ [P.search_mode]: mode === 'keyword' ? null : mode })}
                />
              </span>
            )}
          </div>
        </div>
      </div>

      <FilterDrawer
        open={drawerOpen}
        onClose={() => setDrawerOpen(false)}
        total={data?.total}
        filters={filters}
        meta={meta}
        metaLoading={metaLoading}
        onChange={changeFilters}
        onClearAll={clearAll}
      />

      <div className="mx-auto max-w-7xl space-y-4 px-4 py-5">
        {/* Resume shortcut: match first, or jump back to the matches */}
        {!meLoading && !hasResume && <ResumePrompt jobs={meta?.open_jobs} employers={meta?.companies?.length} />}
        {hasResume && (
          <Link
            to="/resume"
            className="flex items-center justify-between gap-3 rounded-md border border-blue-200 bg-blue-50 px-4 py-2.5 text-sm text-blue-900 hover:bg-blue-100"
          >
            <span>
              <span className="font-semibold">{matches?.items.length ?? 0} jobs fit your resume.</span>{' '}
              See them ranked, with why each one fits.
            </span>
            <ArrowRightIcon className="h-4 w-4 shrink-0" />
          </Link>
        )}

        {/* Result count, sort, layout */}
        <div className="flex flex-wrap items-center justify-between gap-3">
          <h1 className="text-base text-gray-800" aria-live="polite" aria-atomic="true">
            {data ? (
              <>
                <span className="font-semibold text-gray-900">{data.total.toLocaleString()}</span>{' '}
                {level === '' ? 'co-op and internship jobs' : 'jobs'}
                {country === '' ? ' in Canada' : country === 'US' ? ' in the US' : ' in Canada and the US'}
              </>
            ) : 'Loading jobs...'}
          </h1>
          <div className="flex items-center gap-2">
            <label htmlFor="sort-select" className="text-sm text-gray-600">Sort by</label>
            <select
              id="sort-select"
              value={SORTS.some((s) => s.value === sortValue) ? sortValue : 'posted_at:desc'}
              onChange={(e) => {
                const s = SORTS.find((x) => x.value === e.target.value)
                if (s) update({ [P.sort]: s.sort, [P.order]: s.order })
              }}
              className="rounded-md border border-gray-400 bg-white px-2.5 py-1.5 text-sm focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600"
            >
              {SORTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
            <div className="hidden overflow-hidden rounded-md border border-gray-400 bg-white md:inline-flex" role="group" aria-label="Layout">
              <ViewButton active={view === 'cards'} label="List" onClick={() => update({ [P.view]: null })}>
                <GridIcon className="h-4 w-4" />
              </ViewButton>
              <ViewButton active={view === 'table'} label="Table" onClick={() => update({ [P.view]: 'table' })}>
                <ListIcon className="h-4 w-4" />
              </ViewButton>
            </div>
          </div>
        </div>

        <ActiveFilterChips filters={filters} meta={meta} onChange={changeFilters} onClearAll={clearAll} />

        <div className={view === 'cards' ? 'grid gap-4 lg:grid-cols-[minmax(0,25rem)_minmax(0,1fr)]' : ''}>
          <div className="min-w-0 space-y-4">
            <PostingsTable
              data={items}
              isLoading={isLoading}
              isError={isError}
              onRetry={() => refetch()}
              sort={sort}
              order={order}
              onSortChange={(field, dir) => update({ [P.sort]: field, [P.order]: dir })}
              showBookmarks
              onClearFilters={clearAll}
              view={view}
              selectedId={selectedId}
              onSelect={selectJob}
            />

            {data && level === '' && data.total < 15 && (
              <p className="text-sm text-gray-600">
                Co-op and intern roles are posted in waves before each term.{' '}
                <button type="button" className="font-medium text-blue-700 hover:underline" onClick={() => changeFilters({ level: 'entry' })}>
                  Show entry-level jobs too
                </button>
                {country === '' && (
                  <>
                    {' '}or{' '}
                    <button type="button" className="font-medium text-blue-700 hover:underline" onClick={() => changeFilters({ country: 'all' })}>
                      add US internships
                    </button>
                  </>
                )}
                .
              </p>
            )}

            {/* Pagination */}
            {data && data.total > 0 && (
              <nav className="flex flex-col items-center justify-between gap-3 sm:flex-row" aria-label="Pages">
                <div className="flex items-center gap-2 text-sm text-gray-600">
                  <label htmlFor="page-size-select">Per page</label>
                  <select
                    id="page-size-select"
                    value={page_size}
                    onChange={(e) => update({ [P.page_size]: e.target.value, [P.page]: '1' })}
                    className="rounded-md border border-gray-400 bg-white px-2 py-1 text-sm focus:outline-none focus:ring-1 focus:ring-blue-600"
                  >
                    {PAGE_SIZES.map((s) => <option key={s} value={s}>{s}</option>)}
                  </select>
                </div>
                <div className="flex items-center gap-2 text-sm">
                  <button
                    disabled={page <= 1}
                    onClick={() => update({ [P.page]: String(page - 1) })}
                    className="rounded-md border border-gray-400 bg-white px-3 py-1.5 hover:bg-gray-50 disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-blue-600"
                    aria-label="Previous page"
                  >
                    Previous
                  </button>
                  <span className="px-2 text-gray-600">Page {page} of {totalPages}</span>
                  <button
                    disabled={page >= totalPages}
                    onClick={() => update({ [P.page]: String(page + 1) })}
                    className="rounded-md border border-gray-400 bg-white px-3 py-1.5 hover:bg-gray-50 disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-blue-600"
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

          {/* Details of the selected job, next to the list on wide screens */}
          {view === 'cards' && items.length > 0 && (
            <aside
              aria-label="Job details"
              className="hidden lg:sticky lg:top-20 lg:block lg:max-h-[calc(100vh-6rem)] lg:overflow-y-auto rounded-md border border-gray-200 bg-white"
            >
              <PostingDetailPane id={selectedId} />
            </aside>
          )}
        </div>
      </div>
    </div>
  )
}

/** What / Where / Find jobs, like a job board's search bar. */
function JobSearchForm({
  q, province, country, provinces, onSearch,
}: {
  q: string
  province: string
  country: CountryChoice
  provinces: string[]
  onSearch: (what: string, where: string) => void
}) {
  const [what, setWhat] = useState(q)
  const [where, setWhere] = useState(province)
  // Follow the URL when it changes elsewhere (Clear all, a chip, Back)
  useEffect(() => setWhat(q), [q])
  useEffect(() => setWhere(province), [province])

  const canadian = provinces.filter(isProvince)
  const states = provinces.filter((p) => !isProvince(p))

  return (
    <form
      role="search"
      onSubmit={(e) => {
        e.preventDefault()
        onSearch(what.trim(), where)
      }}
      className="flex flex-col gap-2 md:flex-row md:items-stretch md:gap-0 md:rounded-lg md:border md:border-gray-400 md:bg-white md:shadow-sm md:focus-within:border-blue-600"
    >
      <label className="flex flex-1 items-center gap-2.5 rounded-lg border border-gray-400 bg-white px-3.5 md:rounded-none md:border-0">
        <SearchIcon className="h-5 w-5 shrink-0 text-gray-500" />
        <span className="sr-only">What</span>
        <input
          type="search"
          value={what}
          onChange={(e) => setWhat(e.target.value)}
          placeholder="Job title, keyword or company"
          aria-label="Search jobs by title, keyword or company"
          className="w-full border-0 bg-transparent py-3 text-base text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-0"
        />
      </label>
      <span className="hidden w-px self-stretch bg-gray-300 md:my-2 md:block" aria-hidden="true" />
      <label className="flex items-center gap-2.5 rounded-lg border border-gray-400 bg-white px-3.5 md:w-72 md:rounded-none md:border-0">
        <PinIcon className="h-5 w-5 shrink-0 text-gray-500" />
        <span className="sr-only">Where</span>
        <select
          value={where}
          onChange={(e) => {
            setWhere(e.target.value)
            onSearch(what.trim(), e.target.value)
          }}
          aria-label="Where"
          className="w-full border-0 bg-transparent py-3 pl-0 text-base text-gray-900 focus:outline-none focus:ring-0"
        >
          <option value="">{country === 'US' ? 'Anywhere in the US' : country === 'all' ? 'Anywhere' : 'Anywhere in Canada'}</option>
          {country !== 'US' && canadian.length > 0 && (
            <optgroup label="Canada">
              {canadian.map((p) => <option key={p} value={p}>{provinceName(p)}</option>)}
            </optgroup>
          )}
          {country !== '' && states.length > 0 && (
            <optgroup label="United States">
              {states.map((p) => <option key={p} value={p}>{provinceName(p)}</option>)}
            </optgroup>
          )}
        </select>
      </label>
      <button
        type="submit"
        className="rounded-lg bg-blue-600 px-6 py-3 text-base font-semibold text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2 md:m-1.5 md:py-2"
      >
        Find jobs
      </button>
    </form>
  )
}

/** For visitors without a resume: one line pointing at the main feature. */
function ResumePrompt({ jobs, employers }: { jobs?: number; employers?: number }) {
  return (
    <section
      aria-label="Match your resume"
      className="flex flex-col gap-3 rounded-md border border-gray-200 bg-white px-4 py-3.5 sm:flex-row sm:items-center sm:justify-between"
    >
      <div>
        <p className="font-semibold text-gray-900">See which of these jobs fit you</p>
        <p className="text-sm text-gray-600">
          Upload your resume and we'll rank jobs by your program, graduation year and skills.
          {jobs ? ` ${jobs.toLocaleString()} open jobs from ${employers ?? 'real'} employers.` : ''}
        </p>
      </div>
      <div className="flex shrink-0 flex-wrap items-center gap-2">
        <Link
          to="/resume"
          className="inline-flex items-center gap-1.5 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700"
        >
          Upload resume
        </Link>
        <DemoButton variant="header" label="Try a sample" />
      </div>
    </section>
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
