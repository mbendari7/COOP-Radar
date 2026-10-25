/**
 * Job filters.
 *   FilterBar has every filter, laid out as the sidebar next to the results. Work term, level,
 *   location, work mode and job type are always open. Studies, date posted, company and skills
 *   and the rest fold open in place, so nothing ever pops up over the page
 *   ActiveFilterChips shows what is switched on, each one removable, plus Clear all. The jobs
 *   page shows them on phones, where the sidebar is folded away
 *
 * Every value comes from the URL and goes back to it (see PostingsListPage), and all
 * the filtering happens in SQL on the server.
 */

import { useRef, type ReactNode } from 'react'
import type { CategoryKey, FilterMeta } from '../api/postings'
import { isProvince, provinceName, workModeLabel } from '../utils/format'
import {
  COUNTRY_CHOICES, DURATIONS, LEVELS, POSTED_WITHIN, WORK_MODES, countActive, gradYears,
  type CountryChoice, type Filters,
} from './filters'
import { XIcon } from './Icons'
import { LENGTH_BUCKETS, SEASONS, SEASON_DOT, seasonLabel } from './terms'

interface Props {
  filters: Filters
  meta: FilterMeta | undefined
  metaLoading: boolean
  onChange: (patch: Partial<Filters>) => void
  onClearAll: () => void
  /** True when a term or length filter shows only the jobs that name it */
  exact?: boolean
  onExactChange?: (exact: boolean) => void
}

export default function FilterBar({ filters, meta, metaLoading, onChange, onClearAll, exact = false, onExactChange }: Props) {
  const categories = (meta?.categories ?? []).filter(
    (c) => c.count > 0 || filters.category.includes(c.key),
  )
  const countryCount = (code: string) => meta?.countries?.find((c) => c.code === code)?.count
  const modeCount = (key: string) => meta?.work_modes?.find((m) => m.key === key)?.count
  const seasonCount = (key: string) => meta?.seasons?.find((s) => s.key === key)?.count
  const durationCount = (months: number) => meta?.durations?.find((d) => d.months === months)?.count
  // Provinces for Canada, states for the US and both for Canada and US
  const regions = (meta?.provinces ?? []).filter((p) =>
    filters.country === 'all' ? true : filters.country === 'US' ? !isProvince(p) : isProvince(p),
  )
  const termPicked = filters.season.length > 0 || filters.duration.length > 0 || Boolean(filters.term)
  const active = countActive(filters)

  return (
    <div className="divide-y divide-gray-200">
      <div className="flex items-center justify-between pb-3">
        <h2 className="text-[15px] font-bold text-gray-900">Filters</h2>
        {active > 0 && (
          <button type="button" onClick={onClearAll} className="text-sm font-semibold text-air-700 hover:underline">
            Clear all ({active})
          </button>
        )}
      </div>

      <Section title="Work term">
        <ul className="space-y-1.5">
          {SEASONS.map((s) => (
            <li key={s.value}>
              <label className="flex cursor-pointer items-center gap-2.5 text-sm text-gray-800">
                <input
                  type="checkbox"
                  className="h-4 w-4"
                  checked={filters.season.includes(s.value)}
                  onChange={(e) =>
                    onChange({
                      season: e.target.checked
                        ? [...filters.season, s.value]
                        : filters.season.filter((x) => x !== s.value),
                    })
                  }
                />
                <span className={`h-2 w-2 shrink-0 rounded-full ${SEASON_DOT[s.value]}`} aria-hidden="true" />
                <span className="flex-1">
                  {s.label} <span className="text-xs text-gray-500">{s.short}</span>
                </span>
                <Count n={seasonCount(s.value)} />
              </label>
            </li>
          ))}
        </ul>
        <p className="label-form mb-1.5 mt-4">Length</p>
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Length">
          {DURATIONS.map((d) => (
            <Pill
              key={d}
              small
              on={filters.duration.includes(d)}
              count={durationCount(d)}
              onClick={() =>
                onChange({
                  duration: filters.duration.includes(d)
                    ? filters.duration.filter((x) => x !== d)
                    : [...filters.duration, d],
                })
              }
            >
              {LENGTH_BUCKETS[d].label}
            </Pill>
          ))}
        </div>
        {termPicked && onExactChange && (
          <label className="mt-3 flex cursor-pointer items-start gap-2.5 rounded-lg bg-gray-50 p-2.5 text-[13px] text-gray-700">
            <input
              type="checkbox"
              checked={!exact}
              onChange={(e) => onExactChange(!e.target.checked)}
              className="mt-0.5 h-4 w-4 shrink-0"
            />
            <span>
              <span className="font-semibold text-gray-900">Also show jobs that don't say</span>{' '}
              Most employers never write the term. Jobs that name it come first.
            </span>
          </label>
        )}
      </Section>

      <Section title="Experience level">
        <RadioList name="level" options={LEVELS} value={filters.level} onChange={(level) => onChange({ level })} />
      </Section>

      <Section title="Location">
        <RadioList
          name="country"
          options={COUNTRY_CHOICES.map((c) => {
            // No number until the counts load, never a made up 0
            const ca = countryCount('CA')
            const us = countryCount('US')
            const n = c.value === 'all'
              ? (ca === undefined && us === undefined ? undefined : (ca ?? 0) + (us ?? 0))
              : c.value === 'US' ? us : ca
            return { ...c, count: n }
          })}
          value={filters.country}
          onChange={(country: CountryChoice) => onChange({ country, province: '', city: '' })}
        />
        {filters.country !== '' && (
          <p className="mt-1.5 text-xs text-gray-600">US jobs here are student roles like co-op, internships and new grad.</p>
        )}
        <div className="mt-3 space-y-2.5">
          <Select
            id="filter-province"
            label={filters.country === 'US' ? 'State' : filters.country === 'all' ? 'Province or state' : 'Province'}
            value={filters.province}
            loading={metaLoading}
            options={regions.map((p) => ({ value: p, label: provinceName(p) }))}
            onChange={(province) => onChange({ province })}
            placeholder="Anywhere"
          />
          <Select
            id="filter-city"
            label="City"
            value={filters.city}
            loading={metaLoading}
            options={(meta?.cities ?? []).map((c) => ({ value: c, label: c }))}
            onChange={(city) => onChange({ city })}
            placeholder="Any city"
          />
        </div>
      </Section>

      <Section title="Work mode">
        <div className="flex flex-wrap gap-1.5" role="group" aria-label="Work mode">
          {WORK_MODES.map((mode) => (
            <Pill
              key={mode}
              small
              on={filters.work_mode === mode}
              onClick={() => onChange({ work_mode: filters.work_mode === mode ? '' : mode })}
              count={modeCount(mode)}
            >
              {workModeLabel(mode)}
            </Pill>
          ))}
        </div>
      </Section>

      <Section title="Job type">
        {metaLoading && <p className="text-sm text-gray-600">Loading...</p>}
        <ul className="space-y-1.5">
          {categories.map((c) => (
            <li key={c.key}>
              <label className="flex cursor-pointer items-center gap-2.5 text-sm text-gray-800">
                <input
                  type="checkbox"
                  className="h-4 w-4"
                  checked={filters.category.includes(c.key)}
                  onChange={(e) =>
                    onChange({
                      category: e.target.checked
                        ? [...filters.category, c.key]
                        : filters.category.filter((k) => k !== c.key),
                    })
                  }
                />
                <span className="flex-1">{c.label}</span>
                <span className="text-xs tabular-nums text-gray-600">{c.count}</span>
              </label>
            </li>
          ))}
        </ul>
      </Section>

      <Section title="Your studies" fold open={Boolean(filters.program || filters.grad_year)}>
        <div className="space-y-2.5">
          <Select
            id="filter-program"
            label="Program or major"
            value={filters.program}
            loading={metaLoading}
            options={(meta?.programs ?? []).map((p) => ({ value: p.key, label: p.label }))}
            onChange={(program) => onChange({ program: program as Filters['program'] })}
            placeholder="Any program"
          />
          <Select
            id="filter-grad-year"
            label="Graduation year"
            value={filters.grad_year ? String(filters.grad_year) : ''}
            loading={false}
            options={gradYears().map((y) => ({ value: String(y), label: String(y) }))}
            onChange={(y) => onChange({ grad_year: Number(y) || 0 })}
            placeholder="Any year"
          />
        </div>
        <p className="mt-2 text-xs text-gray-600">
          Graduation year is when you finish school, not your work term.
        </p>
      </Section>

      <Section title="Date posted" fold open={filters.posted_within > 0}>
        <RadioList
          name="posted"
          options={POSTED_WITHIN}
          value={filters.posted_within}
          onChange={(posted_within) => onChange({ posted_within })}
        />
      </Section>

      <Section title="Company and skills" fold open={filters.company.length > 0 || filters.skills.length > 0}>
        <Select
          id="filter-company"
          label="Add a company"
          hideLabel
          value=""
          loading={metaLoading}
          options={(meta?.companies ?? [])
            .filter((c) => !filters.company.includes(c))
            .map((c) => ({ value: c, label: c }))}
          onChange={(c) => c && onChange({ company: [...filters.company, c] })}
          placeholder="Add a company"
        />
        <Picked
          items={filters.company}
          onRemove={(c) => onChange({ company: filters.company.filter((x) => x !== c) })}
        />
        <div className="mt-2.5">
          <Select
            id="filter-skills"
            label="Add a skill"
            hideLabel
            value=""
            loading={metaLoading}
            options={(meta?.skills ?? [])
              .filter((s) => !filters.skills.includes(s))
              .map((s) => ({ value: s, label: s }))}
            onChange={(s) => s && onChange({ skills: [...filters.skills, s] })}
            placeholder="Add a skill"
          />
        </div>
        <Picked
          items={filters.skills}
          onRemove={(s) => onChange({ skills: filters.skills.filter((x) => x !== s) })}
        />
        {filters.skills.length > 1 && (
          <p className="mt-2 text-xs text-gray-600">Showing jobs that ask for all of these.</p>
        )}
      </Section>

      <Section title="More" fold open={Boolean(filters.term) || filters.show_expired}>
        <Select
          id="filter-term"
          label="Exact term"
          value={filters.term}
          loading={metaLoading}
          options={(meta?.terms ?? []).filter((t) => t !== 'Open').map((t) => ({ value: t, label: t }))}
          onChange={(term) => onChange({ term })}
          placeholder="Any term"
        />
        <label className="mt-3 flex cursor-pointer items-center gap-2.5 text-sm text-gray-800">
          <input
            type="checkbox"
            className="h-4 w-4"
            checked={filters.show_expired}
            onChange={(e) => onChange({ show_expired: e.target.checked })}
          />
          Include jobs past their deadline
        </label>
      </Section>
    </div>
  )
}

/** The filters that are on, as chips you can remove, above the results. */
export function ActiveFilterChips({
  filters, meta, onChange, onClearAll,
}: Omit<Props, 'metaLoading'>) {
  const rootRef = useRef<HTMLDivElement>(null)
  const label = (key: CategoryKey) => meta?.categories?.find((c) => c.key === key)?.label ?? key
  const programLabel = meta?.programs?.find((p) => p.key === filters.program)?.label ?? filters.program

  /** Once a chip is gone its button goes too, so keep keyboard focus close by. */
  const remove = (patch: Partial<Filters>) => {
    onChange(patch)
    requestAnimationFrame(() => {
      const next = rootRef.current?.querySelector<HTMLElement>('button[aria-label^="Remove filter"]')
      ;(next ?? rootRef.current)?.focus()
    })
  }

  // Level, country and work mode have their own controls in the strip so they get no chip
  const chips: { key: string; text: string; patch: Partial<Filters> }[] = [
    ...filters.category.map((c) => ({
      key: `cat-${c}`, text: label(c), patch: { category: filters.category.filter((x) => x !== c) },
    })),
    ...(filters.program ? [{ key: 'program', text: `Program: ${programLabel}`, patch: { program: '' as const } }] : []),
    ...(filters.grad_year ? [{ key: 'grad', text: `Grad year ${filters.grad_year}`, patch: { grad_year: 0 } }] : []),
    ...(filters.province ? [{ key: 'prov', text: provinceName(filters.province), patch: { province: '' } }] : []),
    ...(filters.city ? [{ key: 'city', text: `City: ${filters.city}`, patch: { city: '' } }] : []),
    ...(filters.posted_within ? [{ key: 'posted', text: POSTED_WITHIN.find((p) => p.value === filters.posted_within)?.label ?? '', patch: { posted_within: 0 } }] : []),
    ...(filters.term ? [{ key: 'term', text: `Term: ${filters.term}`, patch: { term: '' } }] : []),
    ...filters.season.map((s) => ({
      key: `season-${s}`, text: `${seasonLabel(s)} term`, patch: { season: filters.season.filter((x) => x !== s) },
    })),
    ...filters.duration.map((d) => ({
      key: `dur-${d}`, text: LENGTH_BUCKETS[d].label, patch: { duration: filters.duration.filter((x) => x !== d) },
    })),
    ...filters.company.map((c) => ({
      key: `co-${c}`, text: c, patch: { company: filters.company.filter((x) => x !== c) },
    })),
    ...filters.skills.map((s) => ({
      key: `sk-${s}`, text: s, patch: { skills: filters.skills.filter((x) => x !== s) },
    })),
    ...(filters.show_expired ? [{ key: 'exp', text: 'Including past deadlines', patch: { show_expired: false } }] : []),
  ]

  if (chips.length === 0) return null
  return (
    <div ref={rootRef} tabIndex={-1} className="flex flex-wrap items-center gap-2 focus:outline-none">
      {chips.map((c) => (
        <Chip key={c.key} label={c.text} onRemove={() => remove(c.patch)} />
      ))}
      <button
        type="button"
        onClick={onClearAll}
        className="text-sm font-semibold text-gray-700 underline underline-offset-2 hover:text-gray-900"
      >
        Clear all
      </button>
    </div>
  )
}

// Small pieces

/**
 * One group of filters with its heading. With fold it is a details box that opens and closes
 * in place, starting open when one of its filters is on.
 */
function Section({
  title, children, fold = false, open = false,
}: { title: string; children: ReactNode; fold?: boolean; open?: boolean }) {
  if (fold) {
    return (
      <details className="group py-3" open={open}>
        <summary className="flex cursor-pointer list-none items-center justify-between text-[13px] font-semibold text-gray-900 [&::-webkit-details-marker]:hidden">
          {title}
          <span className="text-gray-500 transition-transform group-open:rotate-90" aria-hidden="true">›</span>
        </summary>
        <fieldset className="mt-3">
          <legend className="sr-only">{title}</legend>
          {children}
        </fieldset>
      </details>
    )
  }
  return (
    <fieldset className="py-3.5">
      <legend className="sr-only">{title}</legend>
      <h3 className="mb-2.5 text-[13px] font-semibold text-gray-900" aria-hidden="true">{title}</h3>
      {children}
    </fieldset>
  )
}

export function Pill({
  on, onClick, count, small = false, children,
}: { on: boolean; onClick: () => void; count?: number; small?: boolean; children: ReactNode }) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={on}
      onClick={onClick}
      className={`chip ${small ? 'px-2.5 py-1 text-[13px] shadow-none' : ''} ${on ? 'chip-on' : ''}`}
    >
      {children}
      {count !== undefined && (
        <span className={`text-xs tabular-nums ${on ? 'text-air-100' : 'text-gray-600'}`}>{count.toLocaleString()}</span>
      )}
    </button>
  )
}

function Count({ n }: { n: number | undefined }) {
  return n === undefined ? null : <span className="text-xs tabular-nums text-gray-600">{n.toLocaleString()}</span>
}

function RadioList<T extends string | number>({
  name, options, value, onChange,
}: {
  name: string
  options: { value: T; label: string; count?: number }[]
  value: T
  onChange: (v: T) => void
}) {
  return (
    <div className="space-y-1.5">
      {options.map((o) => (
        <label key={String(o.value)} className="flex cursor-pointer items-center gap-2.5 text-sm text-gray-800">
          <input
            type="radio"
            name={name}
            className="h-4 w-4"
            checked={value === o.value}
            onChange={() => onChange(o.value)}
          />
          <span className="flex-1">{o.label}</span>
          {o.count !== undefined && <span className="text-xs tabular-nums text-gray-600">{o.count.toLocaleString()}</span>}
        </label>
      ))}
    </div>
  )
}

function Select({
  id, label, value, options, loading, onChange, placeholder, hideLabel = false,
}: {
  id: string
  label: string
  value: string
  options: { value: string; label: string }[]
  loading: boolean
  onChange: (v: string) => void
  placeholder: string
  hideLabel?: boolean
}) {
  return (
    <div>
      <label htmlFor={id} className={hideLabel ? 'sr-only' : 'label-form mb-1 block'}>
        {label}
      </label>
      <select
        id={id}
        value={value}
        disabled={loading}
        onChange={(e) => onChange(e.target.value)}
        className="field py-1.5"
      >
        <option value="">{loading ? 'Loading...' : placeholder}</option>
        {options.map((o) => (
          <option key={o.value} value={o.value}>{o.label}</option>
        ))}
      </select>
    </div>
  )
}

function Picked({ items, onRemove }: { items: string[]; onRemove: (v: string) => void }) {
  if (items.length === 0) return null
  return (
    <div className="mt-2 flex flex-wrap gap-1.5">
      {items.map((v) => <Chip key={v} label={v} onRemove={() => onRemove(v)} removeLabel={`Remove ${v}`} />)}
    </div>
  )
}

function Chip({
  label, onRemove, removeLabel = `Remove filter: ${label}`,
}: { label: string; onRemove: () => void; removeLabel?: string }) {
  return (
    <span className="inline-flex items-center gap-1 rounded-sm border-[1.5px] border-air-700 bg-air-50 py-0.5 pl-2.5 pr-1 text-sm font-semibold text-air-800">
      {label}
      <button
        type="button"
        onClick={onRemove}
        aria-label={removeLabel}
        className="rounded-sm p-0.5 text-air-700 hover:bg-air-100 hover:text-air-900"
      >
        <XIcon className="h-3.5 w-3.5" />
      </button>
    </span>
  )
}
