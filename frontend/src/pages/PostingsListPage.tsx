/**
 * The jobs page.
 *
 * A tinted search strip on top with What, Where and Find jobs, and the quick filters under it.
 * Below that the results list on the left and the picked job's details on the right.
 *
 * Everything lives in the URL query string (useSearchParams) so views can be shared, Back from
 * a job brings back the exact list, and a refresh keeps it all. Each change replaces the
 * current history entry so Back leaves the page instead of undoing filters one at a time.
 *
 * The defaults are for students, co-op and internships in Canada. ?level=entry adds entry level
 * jobs and ?level=all shows everything. ?country=US or ?country=all adds US student roles.
 */

import { useCallback, useEffect, useState } from 'react'
import { Link, useSearchParams } from 'react-router-dom'
import {
  useFilterMeta, usePostings,
  type CategoryKey, type PageSize, type PostingListParams, type ProgramKey, type SearchMode, type Season,
  type SortField, type SortOrder, type WorkMode,
} from '../api/postings'
import { useMe } from '../api/auth'
import { usePublicConfig } from '../api/meta'
import { useMatches } from '../api/resume'
import DemoButton from '../components/DemoButton'
import { ActiveFilterChips, FilterDrawer, Pill } from '../components/FilterBar'
import { GetUpdates, NewSinceLastVisit } from '../components/JobUpdates'
import {
  COUNTRY_CHOICES, LEVELS, WORK_MODES, countActive, countriesFor,
  type CountryChoice, type Filters, type Level,
} from '../components/filters'
import { ArrowRightIcon, FilterIcon, ListIcon, PinIcon, SearchIcon, TableIcon } from '../components/Icons'
import { PostingDetailPane } from '../components/PostingDetailView'
import PostingsTable from '../components/PostingsTable'
import { SearchModeToggle } from '../components/SearchModeToggle'
import { SEASONS } from '../components/terms'
import { isProvince, provinceName, workModeLabel } from '../utils/format'

// URL param names live in one place so nobody makes a typo
const P = {
  q: 'q', city: 'city', province: 'province', term: 'term', season: 'season',
  work_mode: 'work_mode', duration: 'duration', skills: 'skills',
  category: 'category', company: 'company', posted_within: 'posted_within',
  show_expired: 'show_expired', search_mode: 'search_mode', level: 'level',
  country: 'country', program: 'program', grad_year: 'grad_year',
  sort: 'sort', order: 'order', view: 'view', job: 'job',
  page: 'page', page_size: 'page_size', added_since: 'added_since', exact: 'exact',
} as const

const PAGE_SIZES: PageSize[] = [10, 25, 50, 100]
const CATEGORY_KEYS: CategoryKey[] = [
  'software', 'data', 'design', 'product', 'hardware', 'it_security', 'business',
  'sales_marketing', 'customer', 'health', 'public', 'trades',
]
const SEASON_KEYS: Season[] = ['winter', 'spring', 'summer', 'fall']

// One menu for the sort field and direction like most job boards
const SORTS: { value: string; label: string; sort: SortField; order: SortOrder }[] = [
  { value: 'posted_at:desc', label: 'Most recent', sort: 'posted_at', order: 'desc' },
  { value: 'first_seen_at:desc', label: 'Newly added to CoopRadar', sort: 'first_seen_at', order: 'desc' },
  { value: 'deadline:asc', label: 'Deadline soonest', sort: 'deadline', order: 'asc' },
  { value: 'company:asc', label: 'Company A to Z', sort: 'company', order: 'asc' },
  { value: 'title:asc', label: 'Job title A to Z', sort: 'title', order: 'asc' },
  { value: 'term_start:asc', label: 'Term starting soonest', sort: 'term_start', order: 'asc' },
  { value: 'duration_months:asc', label: 'Shortest term first', sort: 'duration_months', order: 'asc' },
  { value: 'duration_months:desc', label: 'Longest term first', sort: 'duration_months', order: 'desc' },
]

function readLevel(sp: URLSearchParams): Level {
  const raw = sp.get(P.level)
  if (raw === 'entry' || raw === 'all') return raw
  return ''  // co-op and internships. Older links used level=students for this
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

  // Read everything from the URL with sensible defaults
  const q            = sp.get(P.q) ?? ''
  const city         = sp.get(P.city) ?? ''
  const province     = sp.get(P.province) ?? ''
  const term         = sp.get(P.term) ?? ''
  const season       = sp.getAll(P.season).filter((x): x is Season => SEASON_KEYS.includes(x as Season))
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
  const page_size    = ((PAGE_SIZES.includes(Number(sp.get(P.page_size)) as PageSize) ? Number(sp.get(P.page_size)) : 25)) as PageSize
  // Most employers never write the term or length, so by default a term or length filter also
  // shows jobs that don't say, after the ones that do. exact=1 shows only the ones that say
  const exact        = sp.get(P.exact) === '1'
  const termPicked   = season.length > 0 || duration.length > 0 || Boolean(term)
  const since_raw    = sp.get(P.added_since) ?? ''
  const added_since  = since_raw && !Number.isNaN(Date.parse(since_raw)) ? since_raw : ''

  const filters: Filters = {
    category, level, country, program, grad_year, province, city, work_mode, posted_within,
    term, season, duration, company, skills, show_expired,
  }

  // The filters alone, shared by the list, the new jobs bar and the feed link
  const filterParams: PostingListParams = {
    q: q || undefined,
    city: city || undefined,
    province: province || undefined,
    term: term || undefined,
    season: season.length ? season : undefined,
    work_mode: work_mode || undefined,
    duration: duration.length ? duration : undefined,
    include_unstated: !exact,
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
  }

  // Get the jobs
  const { data, isLoading, isError, refetch } = usePostings({
    ...filterParams,
    added_since: added_since || undefined,
    sort,
    order,
    page,
    page_size,
  })

  const { data: meta, isLoading: metaLoading } = useFilterMeta()

  // Helpers that write to the URL
  const update = useCallback((patches: Record<string, string | string[] | null>) => {
    setSp((prev) => {
      const next = new URLSearchParams(prev)
      // A new filter or sort goes back to page 1 with the first job picked
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
    if ('season' in patch) url[P.season] = patch.season ?? null
    if ('duration' in patch) url[P.duration] = patch.duration?.map(String) ?? null
    if ('company' in patch) url[P.company] = patch.company ?? null
    if ('skills' in patch) url[P.skills] = patch.skills ?? null
    if ('show_expired' in patch) url[P.show_expired] = patch.show_expired ? 'true' : null
    update(url)
  }

  const clearAll = useCallback(() => {
    // Keep the search words and the layout and drop every filter
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
  const first = data && data.total > 0 ? (page - 1) * page_size + 1 : 0
  const last = data ? Math.min(data.total, page * page_size) : 0

  return (
    <div>
      {/* The search strip */}
      <div className="border-b border-gray-300 bg-gray-100">
        <div className="mx-auto max-w-7xl px-4 pb-3 pt-3 md:pb-4 md:pt-5">
          <JobSearchForm
            q={q}
            province={province}
            country={country}
            provinces={meta?.provinces ?? []}
            onSearch={(what, where) => update({ [P.q]: what || null, [P.province]: where || null, [P.city]: null })}
          />

          {/* The filters people change most, one tap each */}
          <div className="-mx-4 mt-3 flex items-center gap-2 overflow-x-auto px-4 pb-1" role="group" aria-label="Quick filters">
            <button type="button" onClick={() => setDrawerOpen(true)} className="chip shrink-0">
              <FilterIcon className="h-4 w-4" />
              All filters
              {active > 0 && (
                <span className="rounded-full bg-post-600 px-1.5 text-xs font-bold text-white">{active}</span>
              )}
            </button>
            <span className="mx-1 h-5 w-px shrink-0 bg-gray-400" aria-hidden="true" />
            <select
              aria-label="Experience level"
              value={level}
              onChange={(e) => changeFilters({ level: e.target.value as Level })}
              className="chip shrink-0 py-1 pl-3 pr-8 focus:border-air-700 focus:outline-none focus:ring-0"
            >
              {LEVELS.map((l) => <option key={l.value} value={l.value}>{l.label}</option>)}
            </select>
            <select
              aria-label="Country"
              value={country}
              onChange={(e) => changeFilters({ country: e.target.value as CountryChoice, province: '', city: '' })}
              className="chip shrink-0 py-1 pl-3 pr-8 focus:border-air-700 focus:outline-none focus:ring-0"
            >
              {COUNTRY_CHOICES.map((c) => <option key={c.value} value={c.value}>{c.label}</option>)}
            </select>
            <select
              aria-label="Term season"
              value={season.length > 1 ? 'several' : season[0] ?? ''}
              onChange={(e) => changeFilters({ season: e.target.value ? [e.target.value as Season] : [] })}
              className={`chip shrink-0 py-1 pl-3 pr-8 focus:border-air-700 focus:outline-none focus:ring-0 ${season.length ? 'chip-on' : ''}`}
            >
              <option value="">Any term</option>
              {season.length > 1 && <option value="several" disabled>{season.length} seasons</option>}
              {SEASONS.map((s) => {
                const n = meta?.seasons?.find((x) => x.key === s.value)?.count
                return <option key={s.value} value={s.value}>{s.label}{n !== undefined ? ` (${n})` : ''}</option>
              })}
            </select>
            <select
              aria-label="Term length"
              value={duration.length > 1 ? 'several' : duration[0] ? String(duration[0]) : ''}
              onChange={(e) => changeFilters({ duration: e.target.value ? [Number(e.target.value)] : [] })}
              className={`chip shrink-0 py-1 pl-3 pr-8 focus:border-air-700 focus:outline-none focus:ring-0 ${duration.length ? 'chip-on' : ''}`}
            >
              <option value="">Any length</option>
              {duration.length > 1 && <option value="several" disabled>{duration.length} lengths</option>}
              {[4, 8, 12, 16].map((d) => {
                const n = meta?.durations?.find((x) => x.months === d)?.count
                return <option key={d} value={d}>{d} months{n !== undefined ? ` (${n})` : ''}</option>
              })}
            </select>
            <span className="mx-1 h-5 w-px shrink-0 bg-gray-400" aria-hidden="true" />
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

      {/* Resume shortcut. Match first, or jump back to the matches */}
      {!meLoading && !hasResume && <ResumePrompt jobs={meta?.open_jobs} employers={meta?.companies?.length} />}
      {hasResume && (
        <Link to="/resume" className="block border-b border-gray-200 bg-air-700 text-white hover:bg-air-800">
          <span className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-2.5 text-sm">
            <span>
              <span className="font-bold">{matches?.items.length ?? 0} jobs fit your resume.</span>{' '}
              See them ranked, with why each one fits.
            </span>
            <ArrowRightIcon className="h-4 w-4 shrink-0" />
          </span>
        </Link>
      )}

      <div className="mx-auto max-w-7xl px-4 pb-8">
        {/* How many, sort and layout */}
        <div className="flex flex-wrap items-end justify-between gap-3 pb-3 pt-4">
          <div>
            <h1 className="display text-[22px] leading-tight text-gray-900 sm:text-[26px]" aria-live="polite" aria-atomic="true">
              {data ? (
                <>
                  {data.total.toLocaleString()}{' '}
                  {level === '' ? 'co-op and internship jobs' : 'jobs'}
                  {country === '' ? ' in Canada' : country === 'US' ? ' in the US' : ' in Canada and the US'}
                </>
              ) : 'Loading jobs...'}
            </h1>
            {data && data.total > 0 && (
              <p className="label-form mt-1">
                Showing {first.toLocaleString()} to {last.toLocaleString()} of {data.total.toLocaleString()}
              </p>
            )}
          </div>
          <div className="flex flex-wrap items-center gap-2">
            <GetUpdates params={filterParams} />
            <label htmlFor="sort-select" className="label-form">Sort by</label>
            <select
              id="sort-select"
              value={SORTS.some((s) => s.value === sortValue) ? sortValue : 'posted_at:desc'}
              onChange={(e) => {
                const s = SORTS.find((x) => x.value === e.target.value)
                if (s) update({ [P.sort]: s.sort, [P.order]: s.order })
              }}
              className="field w-auto py-1.5"
            >
              {SORTS.map((s) => <option key={s.value} value={s.value}>{s.label}</option>)}
            </select>
            <div className="hidden overflow-hidden rounded-lg border border-gray-300 bg-white shadow-sm md:inline-flex" role="group" aria-label="Layout">
              <ViewButton active={view === 'cards'} label="List" onClick={() => update({ [P.view]: null })}>
                <ListIcon className="h-4 w-4" />
              </ViewButton>
              <ViewButton active={view === 'table'} label="Table" onClick={() => update({ [P.view]: 'table' })}>
                <TableIcon className="h-4 w-4" />
              </ViewButton>
            </div>
          </div>
        </div>

        <div className="pb-3 empty:hidden">
          <ActiveFilterChips filters={filters} meta={meta} onChange={changeFilters} onClearAll={clearAll} />
        </div>

        {termPicked && (
          <div className="mb-3 flex flex-wrap items-center gap-x-3 gap-y-1 rounded-lg bg-gray-50 px-3 py-2 text-sm text-gray-700">
            <label className="inline-flex cursor-pointer items-center gap-2 font-semibold text-gray-900">
              <input
                type="checkbox"
                checked={!exact}
                onChange={(e) => update({ [P.exact]: e.target.checked ? null : '1' })}
                className="h-4 w-4 rounded border-gray-400"
              />
              Also show jobs that don't say their term or length
            </label>
            <span>
              {exact
                ? 'Only jobs that name it are shown.'
                : 'Most employers never write it in the post. Jobs that do match come first.'}
            </span>
          </div>
        )}

        <div className="pb-3 empty:hidden">
          {added_since ? (
            <p className="flex flex-wrap items-center gap-2 border border-air-200 bg-air-50 px-3 py-2 text-sm" role="status">
              <span>
                Showing only jobs added since{' '}
                {new Date(added_since).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })}.
              </span>
              <button type="button" className="link font-semibold" onClick={() => update({ [P.added_since]: null })}>
                Show all jobs
              </button>
            </p>
          ) : (
            <NewSinceLastVisit
              params={filterParams}
              active={Boolean(added_since)}
              onShow={(since) => update({ [P.added_since]: since, [P.sort]: 'first_seen_at', [P.order]: 'desc' })}
            />
          )}
        </div>

        <div className={view === 'cards' ? 'grid gap-4 lg:grid-cols-[minmax(0,32rem)_minmax(0,1fr)] xl:grid-cols-[minmax(0,36rem)_minmax(0,1fr)]' : ''}>
          <div className="-mx-4 min-w-0 sm:mx-0">
            <div className="overflow-hidden border-y border-gray-200 bg-white sm:rounded-xl sm:border sm:shadow-sm">
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
            </div>

            <div className="space-y-4 px-4 pt-4 sm:px-0">
              {data && level === '' && data.total < 15 && (
                <p className="text-sm text-gray-700">
                  Co-op and intern roles are posted in waves before each term.{' '}
                  <button type="button" className="link" onClick={() => changeFilters({ level: 'entry' })}>
                    Show entry level jobs too
                  </button>
                  {country === '' && (
                    <>
                      {' '}or{' '}
                      <button type="button" className="link" onClick={() => changeFilters({ country: 'all' })}>
                        add US internships
                      </button>
                    </>
                  )}
                  .
                </p>
              )}

              {/* Pages */}
              {data && data.total > 0 && (
                <nav className="flex flex-col items-center justify-between gap-3 sm:flex-row" aria-label="Pages">
                  <div className="flex items-center gap-2 text-sm text-gray-700">
                    <label htmlFor="page-size-select" className="label-form">Per page</label>
                    <select
                      id="page-size-select"
                      value={page_size}
                      onChange={(e) => update({ [P.page_size]: e.target.value, [P.page]: '1' })}
                      className="field w-auto py-1"
                    >
                      {PAGE_SIZES.map((s) => <option key={s} value={s}>{s}</option>)}
                    </select>
                  </div>
                  <div className="flex items-center gap-2 text-sm">
                    <button
                      disabled={page <= 1}
                      onClick={() => update({ [P.page]: String(page - 1) })}
                      className="btn-secondary px-3 py-1.5"
                      aria-label="Previous page"
                    >
                      Previous
                    </button>
                    <span className="px-2 text-gray-700">Page {page} of {totalPages}</span>
                    <button
                      disabled={page >= totalPages}
                      onClick={() => update({ [P.page]: String(page + 1) })}
                      className="btn-secondary px-3 py-1.5"
                      aria-label="Next page"
                    >
                      Next
                    </button>
                  </div>
                </nav>
              )}
              <p className="text-xs text-gray-600">
                Know a job that's missing? Signed in users can <Link to="/add" className="underline">add it</Link>.
              </p>
            </div>
          </div>

          {/* The picked job's details, next to the list on wide screens */}
          {view === 'cards' && items.length > 0 && (
            <aside
              aria-label="Job details"
              className="card hidden self-start lg:sticky lg:top-[4.5rem] lg:block lg:max-h-[calc(100vh-5.5rem)] lg:overflow-y-auto"
            >
              <PostingDetailPane id={selectedId} />
            </aside>
          )}
        </div>
      </div>
    </div>
  )
}

/** What, Where and Find jobs, like a job board's search bar. */
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
  // Follow the URL when it changes somewhere else, like Clear all, a chip or Back
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
      className="flex flex-col gap-2 md:flex-row md:items-stretch md:gap-0 md:rounded-xl md:border md:border-gray-300 md:bg-white md:p-1.5 md:shadow-sm md:transition md:focus-within:border-air-600 md:focus-within:ring-4 md:focus-within:ring-air-100"
    >
      <label className="flex flex-1 items-center gap-3 rounded-lg border border-gray-300 bg-white px-3 shadow-sm md:border-0 md:px-3 md:shadow-none">
        <SearchIcon className="h-5 w-5 shrink-0 text-gray-700" />
        <span className="sr-only">What</span>
        <input
          type="search"
          value={what}
          onChange={(e) => setWhat(e.target.value)}
          placeholder="Job title, keyword or company"
          aria-label="Search jobs by title, keyword or company"
          className="w-full border-0 bg-transparent py-2.5 text-base text-gray-900 placeholder-gray-500 focus:outline-none focus:ring-0 md:py-2.5 md:text-[17px]"
        />
      </label>
      <span className="hidden w-[1.5px] self-stretch bg-gray-300 md:my-2.5 md:block" aria-hidden="true" />
      <div className="flex gap-2 md:contents">
      <label className="flex min-w-0 flex-1 items-center gap-3 rounded-lg border border-gray-300 bg-white px-3 shadow-sm md:w-72 md:flex-none md:border-0 md:px-3 md:shadow-none">
        <PinIcon className="h-5 w-5 shrink-0 text-gray-700" />
        <span className="sr-only">Where</span>
        <select
          value={where}
          onChange={(e) => {
            setWhere(e.target.value)
            onSearch(what.trim(), e.target.value)
          }}
          aria-label="Where"
          className="w-full border-0 bg-transparent py-2.5 pl-0 text-base text-gray-900 focus:outline-none focus:ring-0 md:py-2.5 md:text-[17px]"
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
      <button type="submit" className="btn-primary shrink-0 px-4 py-2.5 text-base md:px-8">
        Find jobs
      </button>
      </div>
    </form>
  )
}

/** For visitors with no resume yet. One line pointing at the main feature */
function ResumePrompt({ jobs, employers }: { jobs?: number; employers?: number }) {
  return (
    <section aria-label="Match your resume" className="border-b border-gray-200 bg-white">
      <div className="mx-auto flex max-w-7xl items-center justify-between gap-3 px-4 py-2">
        <p className="min-w-0 text-sm text-gray-800">
          <span className="font-bold text-gray-900">See which of these jobs fit you.</span>{' '}
          <span className="hidden md:inline">
            Upload your resume and we'll rank jobs by your program, graduation year and skills.
            {jobs ? ` ${jobs.toLocaleString()} open jobs from ${employers ?? 'real'} employers.` : ''}
          </span>
        </p>
        <div className="flex shrink-0 items-center gap-2">
          <Link to="/resume" className="btn-primary px-3 py-1">Upload resume</Link>
          <span className="hidden sm:inline-flex"><DemoButton variant="secondary" label="Try a sample" /></span>
        </div>
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
      className={`flex items-center gap-1.5 px-2.5 py-1.5 text-sm font-semibold ${active ? 'bg-gray-900 text-white' : 'text-gray-700 hover:text-gray-900'}`}
    >
      {children}
      <span className="sr-only lg:not-sr-only">{label}</span>
    </button>
  )
}
