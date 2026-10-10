/**
 * FilterBar — all filter controls in one place.
 *
 * Each active filter is shown as a removable chip below the controls.
 * "Clear all" removes everything at once.
 * On mobile (<md) the entire bar collapses behind a "Filters" toggle button
 * so it doesn't push the card list off screen.
 */

import { useState } from 'react'
import type { FilterMeta, WorkMode } from '../api/postings'
import { workModeLabel } from '../utils/format'

const WORK_MODES: WorkMode[] = ['onsite', 'hybrid', 'remote']
const DURATIONS = [4, 8, 12, 16]

interface Filters {
  city: string
  province: string
  term: string
  work_mode: WorkMode | ''
  duration: number[]
  skills: string[]
}

interface Props {
  filters: Filters
  meta: FilterMeta | undefined
  metaLoading: boolean
  onChange: (filters: Partial<Filters>) => void
  onClearAll: () => void
}

export default function FilterBar({ filters, meta, metaLoading, onChange, onClearAll }: Props) {
  const [open, setOpen] = useState(false)

  const activeCount = [
    filters.city, filters.province, filters.term, filters.work_mode,
    ...filters.duration, ...filters.skills,
  ].filter(Boolean).length

  return (
    <div className="bg-white border border-gray-200 rounded-lg">
      {/* Mobile toggle */}
      <button
        type="button"
        className="md:hidden w-full flex items-center justify-between px-4 py-3 text-sm font-medium text-gray-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-inset"
        aria-expanded={open}
        aria-controls="filter-panel"
        onClick={() => setOpen((o) => !o)}
      >
        <span>
          Filters
          {activeCount > 0 && (
            <span className="ml-1.5 px-1.5 py-0.5 text-xs bg-brand-500 text-white rounded-full">
              {activeCount}
            </span>
          )}
        </span>
        <span aria-hidden="true" className={`transition-transform ${open ? 'rotate-180' : ''}`}>▾</span>
      </button>

      {/* Filter controls — always visible on md+, collapsible on mobile */}
      <div
        id="filter-panel"
        className={`${open ? 'block' : 'hidden'} md:block p-4`}
      >
        <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4">

          {/* City */}
          <FilterSelect
            id="filter-city"
            label="City"
            value={filters.city}
            options={meta?.cities ?? []}
            loading={metaLoading}
            onChange={(v) => onChange({ city: v })}
          />

          {/* Province */}
          <FilterSelect
            id="filter-province"
            label="Province"
            value={filters.province}
            options={meta?.provinces ?? []}
            loading={metaLoading}
            onChange={(v) => onChange({ province: v })}
          />

          {/* Term */}
          <FilterSelect
            id="filter-term"
            label="Term"
            value={filters.term}
            options={meta?.terms ?? []}
            loading={metaLoading}
            onChange={(v) => onChange({ term: v })}
          />

          {/* Skills multi-select */}
          <FilterSelect
            id="filter-skills"
            label="Add skill"
            value=""
            options={(meta?.skills ?? []).filter((s) => !filters.skills.includes(s))}
            loading={metaLoading}
            onChange={(v) => v && onChange({ skills: [...filters.skills, v] })}
            placeholder="+ Add skill"
          />
        </div>

        {/* Work mode chips */}
        <div className="mt-4">
          <fieldset>
            <legend className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
              Work mode
            </legend>
            <div className="flex flex-wrap gap-2">
              {WORK_MODES.map((mode) => (
                <button
                  key={mode}
                  type="button"
                  role="checkbox"
                  aria-checked={filters.work_mode === mode}
                  onClick={() => onChange({ work_mode: filters.work_mode === mode ? '' : mode })}
                  className={`
                    px-3 py-1 text-sm rounded-full border font-medium
                    focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-1
                    ${filters.work_mode === mode
                      ? 'bg-brand-500 text-white border-brand-500'
                      : 'bg-white text-gray-600 border-gray-300 hover:border-brand-500'}
                  `}
                >
                  {workModeLabel(mode)}
                </button>
              ))}
            </div>
          </fieldset>
        </div>

        {/* Duration checkboxes */}
        <div className="mt-4">
          <fieldset>
            <legend className="text-xs font-medium text-gray-500 uppercase tracking-wide mb-2">
              Duration
            </legend>
            <div className="flex flex-wrap gap-3">
              {DURATIONS.map((d) => (
                <label
                  key={d}
                  className="flex items-center gap-1.5 text-sm text-gray-700 cursor-pointer"
                >
                  <input
                    type="checkbox"
                    className="rounded border-gray-300 text-brand-500 focus:ring-brand-500"
                    checked={filters.duration.includes(d)}
                    onChange={(e) =>
                      onChange({
                        duration: e.target.checked
                          ? [...filters.duration, d]
                          : filters.duration.filter((x) => x !== d),
                      })
                    }
                  />
                  {d} mo
                </label>
              ))}
            </div>
          </fieldset>
        </div>

        {/* Active filter chips + clear all */}
        {activeCount > 0 && (
          <div className="mt-4 flex flex-wrap items-center gap-2">
            <span className="text-xs text-gray-500">Active filters:</span>

            {filters.city && (
              <Chip label={`City: ${filters.city}`} onRemove={() => onChange({ city: '' })} />
            )}
            {filters.province && (
              <Chip label={`Province: ${filters.province}`} onRemove={() => onChange({ province: '' })} />
            )}
            {filters.term && (
              <Chip label={`Term: ${filters.term}`} onRemove={() => onChange({ term: '' })} />
            )}
            {filters.work_mode && (
              <Chip label={workModeLabel(filters.work_mode)} onRemove={() => onChange({ work_mode: '' })} />
            )}
            {filters.duration.map((d) => (
              <Chip
                key={d}
                label={`${d} mo`}
                onRemove={() => onChange({ duration: filters.duration.filter((x) => x !== d) })}
              />
            ))}
            {filters.skills.map((s) => (
              <Chip
                key={s}
                label={s}
                onRemove={() => onChange({ skills: filters.skills.filter((x) => x !== s) })}
              />
            ))}

            <button
              type="button"
              onClick={onClearAll}
              className="text-xs text-red-600 hover:underline focus:outline-none focus:ring-2 focus:ring-red-400 focus:ring-offset-1 rounded"
            >
              Clear all
            </button>
          </div>
        )}
      </div>
    </div>
  )
}

// ── Sub-components ─────────────────────────────────────────────────────────────

function FilterSelect({
  id, label, value, options, loading, onChange, placeholder = 'All',
}: {
  id: string
  label: string
  value: string
  options: string[]
  loading: boolean
  onChange: (v: string) => void
  placeholder?: string
}) {
  return (
    <div>
      <label htmlFor={id} className="block text-xs font-medium text-gray-500 uppercase tracking-wide mb-1">
        {label}
      </label>
      <select
        id={id}
        value={value}
        disabled={loading}
        onChange={(e) => onChange(e.target.value)}
        className="
          w-full text-sm border border-gray-300 rounded-md bg-white px-3 py-2
          focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent
          disabled:opacity-50
        "
      >
        <option value="">{loading ? 'Loading…' : placeholder}</option>
        {options.map((opt) => (
          <option key={opt} value={opt}>{opt}</option>
        ))}
      </select>
    </div>
  )
}

function Chip({ label, onRemove }: { label: string; onRemove: () => void }) {
  return (
    <span className="inline-flex items-center gap-1 px-2 py-0.5 text-xs bg-blue-50 text-blue-700 rounded-full border border-blue-200">
      {label}
      <button
        type="button"
        onClick={onRemove}
        aria-label={`Remove filter: ${label}`}
        className="hover:text-blue-900 focus:outline-none focus:ring-1 focus:ring-blue-500 rounded-full"
      >
        ×
      </button>
    </span>
  )
}
