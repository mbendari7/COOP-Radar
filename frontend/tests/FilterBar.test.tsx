/**
 * FilterBar tests: the sidebar controls, and the removable chips above the results.
 */

import { render, screen, fireEvent, waitFor } from '@testing-library/react'
import { describe, it, expect, vi } from 'vitest'
import FilterBar, { ActiveFilterChips } from '../src/components/FilterBar'
import { EMPTY_FILTERS, type Filters } from '../src/components/filters'
import type { FilterMeta } from '../src/api/postings'

const META: FilterMeta = {
  cities: ['Toronto', 'Waterloo'],
  provinces: ['ON', 'BC', 'TX'],
  terms: ['Summer 2027', 'Winter 2027'],
  skills: ['Python', 'React', 'SQL'],
  companies: ['Lyft', 'Shopify'],
  categories: [
    { key: 'software', label: 'Software & web', count: 12 },
    { key: 'data', label: 'Data & AI', count: 5 },
    { key: 'design', label: 'Design & UX', count: 0 },
  ],
  open_jobs: 17,
  countries: [
    { code: 'CA', label: 'Canada', count: 15 },
    { code: 'US', label: 'United States', count: 2 },
  ],
  work_modes: [
    { key: 'onsite', count: 9 },
    { key: 'hybrid', count: 5 },
    { key: 'remote', count: 3 },
  ],
  programs: [
    { key: 'computer_science', label: 'Computer Science' },
    { key: 'business', label: 'Business / Commerce' },
  ],
}

function renderBar(filters: Filters = EMPTY_FILTERS, onChange = vi.fn(), onClearAll = vi.fn()) {
  return render(
    <FilterBar filters={filters} meta={META} metaLoading={false} onChange={onChange} onClearAll={onClearAll} />,
  )
}

function renderChips(filters: Filters, onChange = vi.fn(), onClearAll = vi.fn()) {
  return render(<ActiveFilterChips filters={filters} meta={META} onChange={onChange} onClearAll={onClearAll} />)
}

describe('FilterBar', () => {
  it('renders location, term, company and skill selects', () => {
    renderBar()
    expect(screen.getByLabelText('Province')).toBeInTheDocument()
    expect(screen.getByLabelText('City')).toBeInTheDocument()
    expect(screen.getByLabelText('Term')).toBeInTheDocument()
    expect(screen.getByLabelText(/add a company/i)).toBeInTheDocument()
    expect(screen.getByLabelText(/add a skill/i)).toBeInTheDocument()
  })

  it('shows provinces by full name', () => {
    renderBar()
    expect(screen.getByRole('option', { name: 'Ontario' })).toBeInTheDocument()
  })

  it('lists job types with counts and hides empty ones', () => {
    renderBar()
    expect(screen.getByLabelText(/Software & web/)).toBeInTheDocument()
    expect(screen.getByText('12')).toBeInTheDocument()
    expect(screen.queryByLabelText(/Design & UX/)).not.toBeInTheDocument()
  })

  it('adds a job type when its box is ticked', () => {
    const onChange = vi.fn()
    renderBar(EMPTY_FILTERS, onChange)
    fireEvent.click(screen.getByLabelText(/Data & AI/))
    expect(onChange).toHaveBeenCalledWith({ category: ['data'] })
  })

  it('sets the date posted filter', () => {
    const onChange = vi.fn()
    renderBar(EMPTY_FILTERS, onChange)
    fireEvent.click(screen.getByLabelText('Past week'))
    expect(onChange).toHaveBeenCalledWith({ posted_within: 7 })
  })

  it('renders work mode buttons', () => {
    renderBar()
    expect(screen.getByRole('checkbox', { name: /on-site/i })).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: /hybrid/i })).toBeInTheDocument()
    expect(screen.getByRole('checkbox', { name: /remote/i })).toBeInTheDocument()
  })

  it('renders length checkboxes for 4, 8, 12, 16 months', () => {
    renderBar()
    for (const d of [4, 8, 12, 16]) expect(screen.getByLabelText(`${d} months`)).toBeInTheDocument()
  })

  it('lists provinces for Canada and states only once the US is chosen', () => {
    const { unmount } = renderBar()
    expect(screen.queryByRole('option', { name: 'Texas' })).not.toBeInTheDocument()
    unmount()
    renderBar({ ...EMPTY_FILTERS, country: 'all' })
    expect(screen.getByRole('option', { name: 'Texas' })).toBeInTheDocument()
    expect(screen.getByLabelText('Province or state')).toBeInTheDocument()
  })

  it('changing country clears the province and city', () => {
    const onChange = vi.fn()
    renderBar({ ...EMPTY_FILTERS, province: 'ON' }, onChange)
    fireEvent.click(screen.getByLabelText(/Canada and US/))
    expect(onChange).toHaveBeenCalledWith({ country: 'all', province: '', city: '' })
  })

  it('sets the program and graduation year', () => {
    const onChange = vi.fn()
    renderBar(EMPTY_FILTERS, onChange)
    fireEvent.change(screen.getByLabelText('Program or major'), { target: { value: 'business' } })
    expect(onChange).toHaveBeenCalledWith({ program: 'business' })
    const year = new Date().getFullYear() + 1
    fireEvent.change(screen.getByLabelText('Graduating in'), { target: { value: String(year) } })
    expect(onChange).toHaveBeenCalledWith({ grad_year: year })
  })

  it('shows work mode counts', () => {
    renderBar()
    expect(screen.getByRole('checkbox', { name: /remote\s*3/i })).toBeInTheDocument()
  })

  it('adds a company from the list', () => {
    const onChange = vi.fn()
    renderBar(EMPTY_FILTERS, onChange)
    fireEvent.change(screen.getByLabelText(/add a company/i), { target: { value: 'Shopify' } })
    expect(onChange).toHaveBeenCalledWith({ company: ['Shopify'] })
  })
})

describe('ActiveFilterChips', () => {
  it('shows nothing when no filters are on', () => {
    const { container } = renderChips(EMPTY_FILTERS)
    expect(container).toBeEmptyDOMElement()
  })

  it('shows a chip for each active filter', () => {
    renderChips({
      ...EMPTY_FILTERS, city: 'Waterloo', skills: ['Python'], category: ['data'], posted_within: 7,
      program: 'computer_science', grad_year: 2028,
    })
    expect(screen.getByText('Program: Computer Science')).toBeInTheDocument()
    expect(screen.getByText('Graduating 2028')).toBeInTheDocument()
    expect(screen.getByText(/City: Waterloo/)).toBeInTheDocument()
    expect(screen.getByText('Python')).toBeInTheDocument()
    expect(screen.getByText('Data & AI')).toBeInTheDocument()
    expect(screen.getByText('Past week')).toBeInTheDocument()
  })

  it('calls onClearAll when "Clear all" is clicked', () => {
    const onClearAll = vi.fn()
    renderChips({ ...EMPTY_FILTERS, city: 'Waterloo' }, vi.fn(), onClearAll)
    fireEvent.click(screen.getByRole('button', { name: /clear all/i }))
    expect(onClearAll).toHaveBeenCalledOnce()
  })

  it('calls onChange with empty city when the city chip is removed', () => {
    const onChange = vi.fn()
    renderChips({ ...EMPTY_FILTERS, city: 'Toronto' }, onChange)
    fireEvent.click(screen.getByRole('button', { name: /Remove filter: City: Toronto/i }))
    expect(onChange).toHaveBeenCalledWith({ city: '' })
  })

  it('keeps keyboard focus on the next chip after removing one', async () => {
    const { rerender } = renderChips({ ...EMPTY_FILTERS, skills: ['Python', 'SQL'] })
    fireEvent.click(screen.getByRole('button', { name: 'Remove filter: Python' }))
    // The parent applies the change: re-render without Python
    rerender(
      <ActiveFilterChips filters={{ ...EMPTY_FILTERS, skills: ['SQL'] }} meta={META} onChange={vi.fn()} onClearAll={vi.fn()} />,
    )
    await waitFor(() =>
      expect(document.activeElement).toBe(screen.getByRole('button', { name: 'Remove filter: SQL' })),
    )
  })
})
