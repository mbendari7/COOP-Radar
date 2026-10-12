/**
 * FilterBar: the job filters, shown as a sidebar on wide screens and behind a
 * "Filters" button on phones. ActiveFilterChips lists what's switched on above the
 * results, each removable, plus "Clear all".
 *
 * Every value comes from and goes back to the URL (see PostingsListPage), and all
 * filtering happens in SQL on the server.
 */

import { useRef, useState, type ReactNode } from 'react'
import type { CategoryKey, FilterMeta } from '../api/postings'
import { provinceName, workModeLabel } from '../utils/format'
import {
  DURATIONS, LEVELS, POSTED_WITHIN, WORK_MODES, countActive, type Filters, type Level,
} from './filters'
import { FilterIcon, XIcon } from './Icons'

interface Props {
  filters: Filters
  meta: FilterMeta | undefined
  metaLoading: boolean
  onChange: (patch: Partial<Filters>) => void
  onClearAll: () => void
}

export default function FilterBar({ filters, meta, metaLoading, onChange, onClearAll }: Props) {
  const [open, setOpen] = useState(false)
  const active = countActive(filters)
  const categories = (meta?.categories ?? []).filter(
    (c) => c.count > 0 || filters.category.includes(c.key),
  )

  return (
    <aside aria-label="Filters" className="lg:sticky lg:top-20">
      {/* Phone toggle */}
      <button
        type="button"
        className="lg:hidden w-full flex items-center justify-between rounded-lg border border-gray-300 bg-white px-4 py-2.5 text-sm font-medium text-gray-800"
        aria-expanded={open}
        aria-controls="filter-panel"
        onClick={() => setOpen((o) => !o)}
      >
        <span className="flex items-center gap-2">
          <FilterIcon className="h-4 w-4" />
          Filters
          {active > 0 && (
            <span className="rounded-full bg-blue-700 px-2 py-0.5 text-xs text-white">{active}</span>
          )}
        </span>
        <span className="text-gray-500">{open ? 'Hide' : 'Show'}</span>
      </button>

      <div
        id="filter-panel"
        className={`${open ? 'block' : 'hidden'} lg:block mt-3 lg:mt-0 rounded-lg border border-gray-200 bg-white divide-y divide-gray-100`}
      >
        <div className="flex items-center justify-between px-4 py-3">
          <h2 className="text-sm font-semibold text-gray-900">Filters</h2>
          {active > 0 && (
            <button type="button" onClick={onClearAll} className="text-sm text-blue-700 hover:underline">
              Reset
            </button>
          )}
        </div>

        <Section title="Job type">
          {metaLoading && <p className="text-sm text-gray-500">Loading...</p>}
          <ul className="space-y-1.5">
            {categories.map((c) => (
              <li key={c.key}>
                <label className="flex items-center gap-2.5 text-sm text-gray-800 cursor-pointer">
                  <input
                    type="checkbox"
                    className="h-4 w-4 rounded border-gray-300 text-blue-700 focus:ring-blue-600"
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
                  <span className="text-xs tabular-nums text-gray-500">{c.count}</span>
                </label>
              </li>
            ))}
          </ul>
        </Section>

        <Section title="Experience level">
          <RadioList
            name="level"
            options={LEVELS}
            value={filters.level}
            onChange={(level) => onChange({ level })}
          />
        </Section>

        <Section title="Location">
          <div className="space-y-3">
            <Select
              id="filter-province"
              label="Province"
              value={filters.province}
              loading={metaLoading}
              options={(meta?.provinces ?? []).map((p) => ({ value: p, label: provinceName(p) }))}
              onChange={(province) => onChange({ province })}
              placeholder="All of Canada"
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
            <p className="text-xs text-gray-500">Remote jobs always show up, wherever you are.</p>
          </div>
        </Section>

        <Section title="Work mode">
          <div className="flex flex-wrap gap-2" role="group" aria-label="Work mode">
            {WORK_MODES.map((mode) => {
              const on = filters.work_mode === mode
              return (
                <button
                  key={mode}
                  type="button"
                  role="checkbox"
                  aria-checked={on}
                  onClick={() => onChange({ work_mode: on ? '' : mode })}
                  className={`rounded-full border px-3 py-1 text-sm ${
                    on
                      ? 'border-blue-700 bg-blue-700 text-white'
                      : 'border-gray-300 bg-white text-gray-700 hover:border-gray-400'
                  }`}
                >
                  {workModeLabel(mode)}
                </button>
              )
            })}
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
              options={(meta?.terms ?? []).map((t) => ({ value: t, label: t }))}
              onChange={(term) => onChange({ term })}
              placeholder="Any term"
            />
            <fieldset>
              <legend className="mb-1.5 text-xs font-medium text-gray-600">Length</legend>
              <div className="grid grid-cols-2 gap-1.5">
                {DURATIONS.map((d) => (
                  <label key={d} className="flex items-center gap-2 text-sm text-gray-800 cursor-pointer">
                    <input
                      type="checkbox"
                      className="h-4 w-4 rounded border-gray-300 text-blue-700 focus:ring-blue-600"
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
            <p className="mt-2 text-xs text-gray-500">Showing jobs that ask for all of these.</p>
          )}
        </Section>

        <div className="px-4 py-3">
          <label className="flex items-center gap-2.5 text-sm text-gray-800 cursor-pointer">
            <input
              type="checkbox"
              className="h-4 w-4 rounded border-gray-300 text-blue-700 focus:ring-blue-600"
              checked={filters.show_expired}
              onChange={(e) => onChange({ show_expired: e.target.checked })}
            />
            Include jobs past their deadline
          </label>
        </div>
      </div>
    </aside>
  )
}

/** The filters that are on, as removable chips above the results. */
export function ActiveFilterChips({
  filters, meta, onChange, onClearAll,
}: Omit<Props, 'metaLoading'>) {
  const rootRef = useRef<HTMLDivElement>(null)
  const label = (key: CategoryKey) => meta?.categories?.find((c) => c.key === key)?.label ?? key

  /** After a chip is removed its button disappears: keep keyboard focus nearby. */
  const remove = (patch: Partial<Filters>) => {
    onChange(patch)
    requestAnimationFrame(() => {
      const next = rootRef.current?.querySelector<HTMLElement>('button[aria-label^="Remove filter"]')
      ;(next ?? rootRef.current)?.focus()
    })
  }

  const chips: { key: string; text: string; patch: Partial<Filters> }[] = [
    ...filters.category.map((c) => ({
      key: `cat-${c}`, text: label(c), patch: { category: filters.category.filter((x) => x !== c) },
    })),
    ...(filters.level ? [{ key: 'level', text: LEVELS.find((l) => l.value === filters.level)?.label ?? '', patch: { level: '' as Level } }] : []),
    ...(filters.province ? [{ key: 'prov', text: `Province: ${provinceName(filters.province)}`, patch: { province: '' } }] : []),
    ...(filters.city ? [{ key: 'city', text: `City: ${filters.city}`, patch: { city: '' } }] : []),
    ...(filters.work_mode ? [{ key: 'mode', text: workModeLabel(filters.work_mode), patch: { work_mode: '' as const } }] : []),
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
        className="text-sm text-gray-600 underline underline-offset-2 hover:text-gray-900"
      >
        Clear all
      </button>
    </div>
  )
}

// ── Pieces ────────────────────────────────────────────────────────────────────

function Section({ title, children }: { title: string; children: ReactNode }) {
  return (
    <fieldset className="px-4 py-4">
      <legend className="sr-only">{title}</legend>
      <h3 className="mb-2.5 text-xs font-semibold uppercase tracking-wider text-gray-500" aria-hidden="true">
        {title}
      </h3>
      {children}
    </fieldset>
  )
}

function RadioList<T extends string | number>({
  name, options, value, onChange,
}: {
  name: string
  options: { value: T; label: string }[]
  value: T
  onChange: (v: T) => void
}) {
  return (
    <div className="space-y-1.5">
      {options.map((o) => (
        <label key={String(o.value)} className="flex items-center gap-2.5 text-sm text-gray-800 cursor-pointer">
          <input
            type="radio"
            name={name}
            className="h-4 w-4 border-gray-300 text-blue-700 focus:ring-blue-600"
            checked={value === o.value}
            onChange={() => onChange(o.value)}
          />
          {o.label}
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
      <label htmlFor={id} className={hideLabel ? 'sr-only' : 'mb-1 block text-xs font-medium text-gray-600'}>
        {label}
      </label>
      <select
        id={id}
        value={value}
        disabled={loading}
        onChange={(e) => onChange(e.target.value)}
        className="w-full rounded-md border border-gray-300 bg-white px-2.5 py-1.5 text-sm text-gray-800 focus:border-blue-600 focus:outline-none focus:ring-1 focus:ring-blue-600 disabled:opacity-50"
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
    <span className="inline-flex items-center gap-1 rounded-full border border-blue-200 bg-blue-50 py-0.5 pl-2.5 pr-1 text-sm text-blue-800">
      {label}
      <button
        type="button"
        onClick={onRemove}
        aria-label={removeLabel}
        className="rounded-full p-0.5 hover:bg-blue-100 focus:outline-none focus:ring-1 focus:ring-blue-600"
      >
        <XIcon className="h-3.5 w-3.5" />
      </button>
    </span>
  )
}
