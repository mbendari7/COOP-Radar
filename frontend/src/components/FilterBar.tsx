/**
 * Job filters.
 *   FilterBar has every filter in sections. Job type, level, program and grad year,
 *   country and place, work mode, date posted, term and length, company and skills
 *   FilterDrawer puts FilterBar in a panel that slides in from the side for All filters.
 *   The most used filters also sit in the strip above the results
 *   ActiveFilterChips shows what is switched on, each one removable, plus Clear all
 *
 * Every value comes from the URL and goes back to it (see PostingsListPage), and all
 * the filtering happens in SQL on the server.
 */

import { useEffect, useRef, type ReactNode } from 'react'
import type { CategoryKey, FilterMeta } from '../api/postings'
import { isProvince, provinceName, workModeLabel } from '../utils/format'
import {
  COUNTRY_CHOICES, DURATIONS, LEVELS, POSTED_WITHIN, WORK_MODES, gradYears,
  type CountryChoice, type Filters,
} from './filters'
import { XIcon } from './Icons'

interface Props {
  filters: Filters
  meta: FilterMeta | undefined
  metaLoading: boolean
  onChange: (patch: Partial<Filters>) => void
  onClearAll: () => void
}

export default function FilterBar({ filters, meta, metaLoading, onChange }: Props) {
  const categories = (meta?.categories ?? []).filter(
    (c) => c.count > 0 || filters.category.includes(c.key),
  )
  const countryCount = (code: string) => meta?.countries?.find((c) => c.code === code)?.count
  const modeCount = (key: string) => meta?.work_modes?.find((m) => m.key === key)?.count
  // Provinces for Canada, states for the US and both for Canada and US
  const regions = (meta?.provinces ?? []).filter((p) =>
    filters.country === 'all' ? true : filters.country === 'US' ? !isProvince(p) : isProvince(p),
  )

  return (
    <div className="divide-y divide-gray-300">
      <Section title="Job type">
        {metaLoading && <p className="text-sm text-gray-600">Loading...</p>}
        <ul className="grid gap-1.5 sm:grid-cols-2">
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

      <Section title="Experience level">
        <RadioList name="level" options={LEVELS} value={filters.level} onChange={(level) => onChange({ level })} />
      </Section>

      <Section title="Your studies">
        <div className="grid gap-3 sm:grid-cols-2">
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
            label="Graduating in"
            value={filters.grad_year ? String(filters.grad_year) : ''}
            loading={false}
            options={gradYears().map((y) => ({ value: String(y), label: String(y) }))}
            onChange={(y) => onChange({ grad_year: Number(y) || 0 })}
            placeholder="Any year"
          />
        </div>
        <p className="mt-2 text-xs text-gray-600">
          Program shows jobs that name it or fit it. Graduation year hides jobs that ask for a different one.
        </p>
      </Section>

      <Section title="Country and location">
        <RadioList
          name="country"
          options={COUNTRY_CHOICES.map((c) => {
            const n = c.value === 'all'
              ? (countryCount('CA') ?? 0) + (countryCount('US') ?? 0)
              : countryCount(c.value === 'US' ? 'US' : 'CA')
            return { ...c, count: n }
          })}
          value={filters.country}
          onChange={(country: CountryChoice) => onChange({ country, province: '', city: '' })}
        />
        {filters.country !== '' && (
          <p className="mt-1.5 text-xs text-gray-600">US jobs here are student roles like co-op, internships and new grad.</p>
        )}
        <div className="mt-3 grid gap-3 sm:grid-cols-2">
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
        <p className="mt-2 text-xs text-gray-600">Remote jobs show up for every city.</p>
      </Section>

      <Section title="Work mode">
        <div className="flex flex-wrap gap-2" role="group" aria-label="Work mode">
          {WORK_MODES.map((mode) => (
            <Pill
              key={mode}
              on={filters.work_mode === mode}
              onClick={() => onChange({ work_mode: filters.work_mode === mode ? '' : mode })}
              count={modeCount(mode)}
            >
              {workModeLabel(mode)}
            </Pill>
          ))}
        </div>
      </Section>

      <Section title="Date posted">
        <RadioList
          name="posted"
          options={POSTED_WITHIN}
          value={filters.posted_within}
          onChange={(posted_within) => onChange({ posted_within })}
        />
      </Section>

      <Section title="Term and length">
        <div className="space-y-3">
          <Select
            id="filter-term"
            label="Term"
            value={filters.term}
            loading={metaLoading}
            options={(meta?.terms ?? []).filter((t) => t !== 'Open').map((t) => ({ value: t, label: t }))}
            onChange={(term) => onChange({ term })}
            placeholder="Any term"
          />
          <fieldset>
            <legend className="label-form mb-1.5">Length</legend>
            <div className="flex flex-wrap gap-x-5 gap-y-1.5">
              {DURATIONS.map((d) => (
                <label key={d} className="flex cursor-pointer items-center gap-2 text-sm text-gray-800">
                  <input
                    type="checkbox"
                    className="h-4 w-4"
                    checked={filters.duration.includes(d)}
                    onChange={(e) =>
                      onChange({
                        duration: e.target.checked
                          ? [...filters.duration, d]
                          : filters.duration.filter((x) => x !== d),
                      })
                    }
                  />
                  {d} months
                </label>
              ))}
            </div>
          </fieldset>
        </div>
      </Section>

      <Section title="Company">
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
      </Section>

      <Section title="Skills">
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
        <Picked
          items={filters.skills}
          onRemove={(s) => onChange({ skills: filters.skills.filter((x) => x !== s) })}
        />
        {filters.skills.length > 1 && (
          <p className="mt-2 text-xs text-gray-600">Showing jobs that ask for all of these.</p>
        )}
      </Section>

      <div className="py-4">
        <label className="flex cursor-pointer items-center gap-2.5 text-sm text-gray-800">
          <input
            type="checkbox"
            className="h-4 w-4"
            checked={filters.show_expired}
            onChange={(e) => onChange({ show_expired: e.target.checked })}
          />
          Include jobs past their deadline
        </label>
      </div>
    </div>
  )
}

/** All filters. The whole FilterBar in a side panel with the live job count. */
export function FilterDrawer({
  open, onClose, total, ...props
}: Props & { open: boolean; onClose: () => void; total: number | undefined }) {
  const closeRef = useRef<HTMLButtonElement>(null)

  useEffect(() => {
    if (!open) return
    closeRef.current?.focus()
    const onKey = (e: KeyboardEvent) => e.key === 'Escape' && onClose()
    document.addEventListener('keydown', onKey)
    const overflow = document.body.style.overflow
    document.body.style.overflow = 'hidden'
    return () => {
      document.removeEventListener('keydown', onKey)
      document.body.style.overflow = overflow
    }
  }, [open, onClose])

  if (!open) return null
  return (
    <div className="fixed inset-0 z-50 flex">
      <div className="absolute inset-0 bg-gray-950/50" onClick={onClose} aria-hidden="true" />
      <div
        role="dialog"
        aria-modal="true"
        aria-labelledby="filters-title"
        className="relative flex h-full w-full max-w-lg flex-col bg-white shadow-xl"
      >
        <div className="flex items-center justify-between bg-post-600 px-5 py-3.5 text-white">
          <h2 id="filters-title" className="stretch-condensed text-xl font-extrabold uppercase tracking-[0.03em]">All filters</h2>
          <button
            ref={closeRef}
            type="button"
            onClick={onClose}
            aria-label="Close filters"
            className="rounded-sm p-1 text-white hover:bg-white/15"
          >
            <XIcon className="h-5 w-5" />
          </button>
        </div>
        <div className="flex-1 overflow-y-auto px-5">
          <FilterBar {...props} />
        </div>
        <div className="flex items-center justify-between gap-3 border-t-[1.5px] border-gray-900 px-5 py-3">
          <button type="button" onClick={props.onClearAll} className="text-sm font-semibold text-gray-800 hover:underline">
            Reset all
          </button>
          <button type="button" onClick={onClose} className="btn-primary px-5">
            {total === undefined ? 'Show jobs' : `Show ${total.toLocaleString()} job${total === 1 ? '' : 's'}`}
          </button>
        </div>
      </div>
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
    ...(filters.grad_year ? [{ key: 'grad', text: `Graduating ${filters.grad_year}`, patch: { grad_year: 0 } }] : []),
    ...(filters.province ? [{ key: 'prov', text: provinceName(filters.province), patch: { province: '' } }] : []),
    ...(filters.city ? [{ key: 'city', text: `City: ${filters.city}`, patch: { city: '' } }] : []),
    ...(filters.posted_within ? [{ key: 'posted', text: POSTED_WITHIN.find((p) => p.value === filters.posted_within)?.label ?? '', patch: { posted_within: 0 } }] : []),
    ...(filters.term ? [{ key: 'term', text: `Term: ${filters.term}`, patch: { term: '' } }] : []),
    ...filters.duration.map((d) => ({
      key: `dur-${d}`, text: `${d} months`, patch: { duration: filters.duration.filter((x) => x !== d) },
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

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset className="py-4">
      <legend className="sr-only">{title}</legend>
      <h3 className="label-form mb-3 !text-gray-900" aria-hidden="true">{title}</h3>
      {children}
    </fieldset>
  )
}

export function Pill({
  on, onClick, count, children,
}: { on: boolean; onClick: () => void; count?: number; children: ReactNode }) {
  return (
    <button
      type="button"
      role="checkbox"
      aria-checked={on}
      onClick={onClick}
      className={`chip ${on ? 'chip-on' : ''}`}
    >
      {children}
      {count !== undefined && (
        <span className={`text-xs tabular-nums ${on ? 'text-air-100' : 'text-gray-600'}`}>{count.toLocaleString()}</span>
      )}
    </button>
  )
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
