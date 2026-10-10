/**
 * PostingsTable tests — renders rows, sort header clicks update URL params.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { render, screen, fireEvent } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useSearchParams } from 'react-router-dom'
import { describe, it, expect, vi } from 'vitest'
import PostingsTable from '../src/components/PostingsTable'
import type { PostingListItem } from '../src/api/postings'

// --- Helpers -----------------------------------------------------------------

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
    <QueryClient>
      <MemoryRouter>
        <QueryClientProvider client={qc}>
          <PostingsTable {...defaults} />
        </QueryClientProvider>
      </MemoryRouter>
    </QueryClient>
  )
}

// --- Tests -------------------------------------------------------------------

describe('PostingsTable', () => {
  it('shows empty state when data is empty', () => {
    renderTable({ data: [] })
    expect(screen.getByText(/No postings match/i)).toBeInTheDocument()
  })

  it('shows error state and retry button on error', () => {
    const onRetry = vi.fn()
    renderTable({ isError: true, onRetry })
    expect(screen.getByText(/Something went wrong/i)).toBeInTheDocument()

    fireEvent.click(screen.getByRole('button', { name: /try again/i }))
    expect(onRetry).toHaveBeenCalledOnce()
  })

  it('renders posting rows in the desktop table', () => {
    const data = [
      makePosting({ title: 'Backend Dev', company: 'Shopify' }),
      makePosting({ title: 'Frontend Dev', company: 'Wealthsimple' }),
    ]
    renderTable({ data })

    // Both titles visible in the table (hidden on mobile in the DOM but in the table)
    expect(screen.getAllByText('Backend Dev').length).toBeGreaterThan(0)
    expect(screen.getAllByText('Frontend Dev').length).toBeGreaterThan(0)
  })

  it('calls onSortChange with correct args when a sortable header is clicked', () => {
    const onSortChange = vi.fn()
    const data = [makePosting()]
    renderTable({ data, sort: 'posted_at', order: 'desc', onSortChange })

    // Click the "Deadline" column header
    const deadlineHeader = screen.getByRole('columnheader', { name: /deadline/i })
    fireEvent.click(deadlineHeader)

    expect(onSortChange).toHaveBeenCalledWith('deadline', 'desc')
  })

  it('toggles sort order on second click of the same column', () => {
    const onSortChange = vi.fn()
    const data = [makePosting()]
    // Already sorted by deadline asc
    renderTable({ data, sort: 'deadline', order: 'asc', onSortChange })

    const deadlineHeader = screen.getByRole('columnheader', { name: /deadline/i })
    fireEvent.click(deadlineHeader)

    // Second click should toggle to desc
    expect(onSortChange).toHaveBeenCalledWith('deadline', 'desc')
  })
})
