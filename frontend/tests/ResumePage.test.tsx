/**
 * ResumePage tests — a signed-out visitor can upload straight away: a guest account is
 * created first, then the resume is uploaded.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import ResumePage from '../src/pages/ResumePage'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

const CONFIG = { demo_enabled: true, server_ai_enabled: false, semantic_search_enabled: false, ai_daily_limit: 20 }
const GUEST = { id: 'u1', email: 'demo-1@demo.coopradar', created_at: '', is_admin: false, is_demo: true }

function renderPage() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <MemoryRouter>
      <QueryClientProvider client={qc}>
        <ResumePage />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('ResumePage', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('creates a guest account, then uploads, when a signed-out visitor drops a resume', async () => {
    const calls: string[] = []
    const fetchMock = vi.fn((url: string, init?: RequestInit) => {
      calls.push(`${init?.method ?? 'GET'} ${url}`)
      if (url === '/api/config') return Promise.resolve(json(CONFIG))
      if (url === '/api/me') return Promise.resolve(json({ detail: 'Not signed in', code: 'UNAUTHENTICATED' }, 401))
      if (url === '/api/auth/guest') return Promise.resolve(json(GUEST, 201))
      if (url === '/api/resume' && init?.method === 'POST') {
        return Promise.resolve(json({ resume: { id: 'r1', filename: 'cv.pdf', file_size: 10, uploaded_at: '2026-10-11T00:00:00Z' }, matches: [] }))
      }
      if (url === '/api/resume/matches') return Promise.resolve(json({ items: [], resume: null }))
      return Promise.resolve(json({}))
    })
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    const input = await screen.findByLabelText(/drop your resume here/i)
    const file = new File(['%PDF-1.4'], 'cv.pdf', { type: 'application/pdf' })
    fireEvent.change(input, { target: { files: [file] } })

    await waitFor(() => expect(calls).toContain('POST /api/resume'))
    expect(calls.indexOf('POST /api/auth/guest')).toBeLessThan(calls.indexOf('POST /api/resume'))
  })

  it('rejects files that are not PDF or DOCX before uploading', async () => {
    const fetchMock = vi.fn((url: string) =>
      Promise.resolve(url === '/api/config' ? json(CONFIG) : json({ detail: 'x', code: 'UNAUTHENTICATED' }, 401)),
    )
    vi.stubGlobal('fetch', fetchMock)
    renderPage()

    const input = await screen.findByLabelText(/drop your resume here/i)
    fireEvent.change(input, { target: { files: [new File(['x'], 'cv.png', { type: 'image/png' })] } })

    expect(await screen.findByRole('alert')).toHaveTextContent(/PDF or Word/i)
    expect(fetchMock).not.toHaveBeenCalledWith('/api/auth/guest', expect.anything())
  })
})
