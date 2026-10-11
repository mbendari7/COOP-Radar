/**
 * FilterBar tests — renders controls, chip removal, clear-all.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import FilterBar from '../src/components/FilterBar'
import type { FilterMeta } from '../src/api/postings'

const META: FilterMeta = {
  cities: ['Toronto', 'Waterloo'],
  provinces: ['ON', 'BC'],
  terms: ['Summer 2027', 'Winter 2027'],
  skills: ['Python', 'React', 'SQL'],
}

type Filters = React.ComponentProps<typeof FilterBar>['filters']

const EMPTY_FILTERS: Filters = {
  city: '', province: '', term: '', work_mode: '',
  duration: [], skills: [],
}

function renderBar(
  filters: Filters = EMPTY_FILTERS,
  onChange = vi.fn(),
  onClearAll = vi.fn(),
) {
  return render(
    <FilterBar
      filters={filters}
      meta={META}
      metaLoading={false}
      onChange={onChange}
      onClearAll={onClearAll}
    />
  )
}

describe('FilterBar', () => {
  it('renders city, province, term, and skill selects', () => {
    renderBar()
    expect(screen.getByLabelText(/city/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/province/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/term/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/add skill/i)).toBeInTheDocument()
  })

  it('renders work mode buttons', () => {
    renderBar()
    expect(screen.getByRole('checkbox', { name: /on-site/i })).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: /hybrid/i })).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: /remote/i })).toBeInTheDocument()
  })

  it('renders duration checkboxes for 4, 8, 12, 16 months', () => {
    renderBar()
    expect(screen.getByLabelText('4 mo')).toBeInTheDocument()
    expect(screen.getByLabelText('8 mo')).toBeInTheDocument()
    expect(screen.getByLabelText('12 mo')).toBeInTheDocument()
    expect(screen.getByLabelText('16 mo')).toBeInTheDocument()
  })

  it('shows active filter chips when filters are set', () => {
    renderBar({ ...EMPTY_FILTERS, city: 'Waterloo', skills: ['Python'] })
    expect(screen.getByText(/City: Waterloo/)).toBeInTheDocument()
    expect(screen.getByText('Python')).toBeInTheDocument()
  })

  it('calls onClearAll when "Clear all" is clicked', () => {
    const onClearAll = vi.fn()
    renderBar({ ...EMPTY_FILTERS, city: 'Waterloo' }, vi.fn(), onClearAll)

    fireEvent.click(screen.getByRole('button', { name: /clear all/i }))
    expect(onClearAll).toHaveBeenCalledOnce()
  })

  it('calls onChange with empty city when city chip × is clicked', () => {
    const onChange = vi.fn()
    renderBar({ ...EMPTY_FILTERS, city: 'Toronto' }, onChange)

    fireEvent.click(screen.getByRole('button', { name: /Remove filter: City: Toronto/i }))
    expect(onChange).toHaveBeenCalledWith({ city: '' })
  })

  it('keeps keyboard focus on the next chip after removing one', async () => {
    const { rerender } = renderBar({ ...EMPTY_FILTERS, skills: ['Python', 'SQL'] })
    fireEvent.click(screen.getByRole('button', { name: 'Remove filter: Python' }))
    // The parent applies the change: re-render without Python
    rerender(
      <FilterBar
        filters={{ ...EMPTY_FILTERS, skills: ['SQL'] }}
        meta={META}
        metaLoading={false}
        onChange={vi.fn()}
        onClearAll={vi.fn()}
      />,
    )
    await waitFor(() =>
      expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Remove filter: SQL' })),
    )
  })
})
