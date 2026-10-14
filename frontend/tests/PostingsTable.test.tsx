/**
 * Tests for the job list and table. Rows show up and clicking a header changes the sort.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect, vi } from 'vitest'
import PostingsTable from '../src/components/PostingsTable'
import type { PostingListItem } from '../src/api/postings'

// Helpers

function makePosting(overrides: Partial<PostingListItem> = {}): PostingListItem {
  return {
    id: crypto.randomUUID(),
    title: 'Software Developer',
    company: 'Acme',
    city: 'Waterloo',
    province: 'ON',
    work_mode: 'hybrid',
    term: 'Summer 2027',
    duration_months: 4,
    deadline: '2027-02-28',
    posted_at: '2026-09-15T10:00:00Z',
    skills: ['Python', 'SQL'],
    source_url: null,
    closed_at: null,
    source_id: null,
    country: 'CA',
    grad_years: [],
    fields_of_study: [],
    role: 'job',
    season: 'summer',
    term_start: '2027-05-01',
    ...overrides,
  }
}

/** Wrap the component in the providers it needs. */
function renderTable(props: Partial<React.ComponentProps<typeof PostingsTable>> = {}) {
  const qc = new QueryClient()
  const defaults: React.ComponentProps<typeof PostingsTable> = {
    data: [],
    isLoading: false,
    isError: false,
    onRetry: vi.fn(),
    sort: 'posted_at',
    order: 'desc',
    onSortChange: vi.fn(),
    ...props,
  }

  return render(
    <MemoryRouter>
      <QueryClientProvider client={qc}>
        <PostingsTable {...defaults} />
      </QueryClientProvider>
    </MemoryRouter>
  )
}

// Tests

describe('PostingCard', () => {
  it('shows the kind of role, the term and a US location', () => {
    renderTable({
      view: 'cards',
      data: [makePosting({ title: 'Data Co-op', role: 'coop', city: 'Austin', province: 'TX', country: 'US' })],
    })
    expect(screen.getByText('Co-op')).toBeInTheDocument()
    // The term and its length read together, like "Summer 2027 · 4 months"
    expect(screen.getByText('Summer 2027 · 4 months')).toBeInTheDocument()
    expect(screen.getAllByText(/Austin, TX, US/).length).toBeGreaterThan(0)
  })

  it('leaves the term out when the job does not say, and shows a length on its own', () => {
    renderTable({
      view: 'cards',
      data: [makePosting({ title: 'No term', term: 'Open', season: null, duration_months: 8 })],
    })
    expect(screen.queryByText(/Open/)).not.toBeInTheDocument()
    expect(screen.getByText('8 months')).toBeInTheDocument()
  })

  it('sorts the table by term length when the Length header is clicked', () => {
    const onSortChange = vi.fn()
    renderTable({ view: 'table', data: [makePosting()], onSortChange })
    fireEvent.click(screen.getByRole('columnheader', { name: /Length/ }))
    expect(onSortChange).toHaveBeenCalledWith('duration_months', expect.stringMatching(/asc|desc/))
  })

  it('marks the selected job for the details panel', () => {
    const posting = makePosting({ title: 'Picked' })
    renderTable({ view: 'cards', data: [posting, makePosting()], selectedId: posting.id })
    expect(screen.getByRole('article', { name: /Picked at Acme/ })).toHaveAttribute('aria-current', 'true')
  })
})

describe('PostingsTable', () => {
  it('shows empty state when data is empty', () => {
    renderTable({ data: [] })
    expect(screen.getByText(/No jobs match/i)).toBeInTheDocument()
  })

  it('shows error state and retry button on error', () => {
    const onRetry = vi.fn()
    renderTable({ isError: true, onRetry })
    expect(screen.getByText(/didn't load/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('renders posting rows in the desktop table', () => {
    const data = [
      makePosting({ title: 'Backend Dev', company: 'Shopify' }),
      makePosting({ title: 'Frontend Dev', company: 'Wealthsimple' }),
    ]
    renderTable({ data })

    // Both titles show in the table. They are hidden on phones but still in the table
    expect(screen.getAllByText('Backend Dev').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Frontend Dev').length).toBeGreaterThan(0)
  })

  it('keeps every header above its own column when bookmarks are shown', () => {
    renderTable({ data: [makePosting({ title: 'Backend Dev', company: 'Shopify' })], showBookmarks: true })
    const table = screen.getByRole('table', { name: /co-op postings/i })
    const headers = Array.from(table.querySelectorAll('thead th')).map((th) => th.textContent ?? '')
    const cells = Array.from(table.querySelectorAll('tbody tr:first-child td'))
    expect(cells).toHaveLength(headers.length)
    const roleIdx = headers.findIndex((h) => /role/i.test(h))
    const companyIdx = headers.findIndex((h) => /company/i.test(h))
    expect(cells[roleIdx]).toHaveTextContent('Backend Dev')
    expect(cells[companyIdx]).toHaveTextContent('Shopify')
  })

  it('marks live employer jobs and never shows a dangling comma for remote jobs', () => {
    renderTable({ data: [makePosting({ title: 'Data Intern', city: 'Remote', province: '', source_id: 'src-1' })] })
    expect(screen.getAllByText('Live').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Remote').length).toBeGreaterThan(0)
    expect(screen.queryByText('Remote,')).not.toBeInTheDocument()
  })

  it('calls onSortChange with correct args when a sortable header is clicked', () => {
    const onSortChange = vi.fn()
    const data = [makePosting()]
    renderTable({ data, sort: 'posted_at', order: 'desc', onSortChange })

    // Click the Deadline column header
    const deadlineHeader = screen.getByRole('columnheader', { name: /deadline/i })
    fireEvent.click(deadlineHeader)

    // The first click on a new column sorts up, soonest deadline first
    expect(onSortChange).toHaveBeenCalledWith('deadline', 'asc')
  })

  it('toggles sort order on second click of the same column', () => {
    const onSortChange = vi.fn()
    const data = [makePosting()]
    // Already sorted by deadline going up
    renderTable({ data, sort: 'deadline', order: 'asc', onSortChange })

    const deadlineHeader = screen.getByRole('columnheader', { name: /deadline/i })
    fireEvent.click(deadlineHeader)

    // The second click should flip it to going down
    expect(onSortChange).toHaveBeenCalledWith('deadline', 'desc')
  })
})
