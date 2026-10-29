/**
 * Tests for the snapshot that makes the jobs page open at once: the copy saved in the browser
 * shows before the server answers, and a fresh one gets saved for next time.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { renderHook, waitFor } from '@testing-library/react'
import type { ReactNode } from 'react'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import { useSnapshot, type PostingsSnapshot } from '../src/api/postings'

const KEY = 'coopradar:snapshot'

function snapshot(title: string): PostingsSnapshot {
  return {
    postings: {
      items: [{ id: 'job-1', title } as PostingsSnapshot['postings']['items'][number]],
      total: 1, page: 1, page_size: 25,
    },
    filters: { cities: [], provinces: [], terms: [], skills: [] } as unknown as PostingsSnapshot['filters'],
    first_job: null,
  }
}

function wrapper() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return ({ children }: { children: ReactNode }) => (
    <QueryClientProvider client={qc}>{children}</QueryClientProvider>
  )
}

describe('useSnapshot', () => {
  beforeEach(() => localStorage.clear())
  afterEach(() => vi.unstubAllGlobals())

  it('shows the saved copy right away while the server is still asleep', () => {
    localStorage.setItem(KEY, JSON.stringify({ data: snapshot('Saved Co-op'), savedAt: 1 }))
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))  // never answers

    const { result } = renderHook(() => useSnapshot(), { wrapper: wrapper() })

    expect(result.current.data?.postings.items[0].title).toBe('Saved Co-op')
  })

  it('saves a fresh copy for next time', async () => {
    vi.stubGlobal('fetch', vi.fn(async () => new Response(JSON.stringify(snapshot('Fresh Co-op')))))

    const { result } = renderHook(() => useSnapshot(), { wrapper: wrapper() })

    await waitFor(() => expect(result.current.data?.postings.items[0].title).toBe('Fresh Co-op'))
    expect(JSON.parse(localStorage.getItem(KEY) ?? '{}').data.postings.items[0].title).toBe('Fresh Co-op')
  })

  it('ignores a broken saved copy', () => {
    localStorage.setItem(KEY, '{not json')
    vi.stubGlobal('fetch', vi.fn(() => new Promise(() => {})))

    const { result } = renderHook(() => useSnapshot(), { wrapper: wrapper() })

    expect(result.current.data).toBeUndefined()
  })
})
