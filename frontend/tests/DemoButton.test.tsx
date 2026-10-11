/**
 * DemoButton tests — hidden when demo accounts are off; one click creates a demo session.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import DemoButton from '../src/components/DemoButton'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function renderButton() {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <MemoryRouter>
      <QueryClientProvider client={qc}>
        <DemoButton />
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

describe('DemoButton', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('renders nothing when the server has demo accounts off', async () => {
    const fetchMock = vi.fn().mockResolvedValue(json({ demo_enabled: false, server_ai_enabled: false, semantic_search_enabled: false, ai_daily_limit: 20 }))
    vi.stubGlobal('fetch', fetchMock)
    renderButton()
    await waitFor(() => expect(fetchMock).toHaveBeenCalled())
    expect(screen.queryByRole('button', { name: /try the demo/i })).not.toBeInTheDocument()
  })

  it('creates a demo session when clicked', async () => {
    const fetchMock = vi.fn((url: string) =>
      Promise.resolve(
        url === '/api/config'
          ? json({ demo_enabled: true, server_ai_enabled: false, semantic_search_enabled: false, ai_daily_limit: 20 })
          : json({ id: '1', email: 'demo-1@demo.coopradar', created_at: '', is_admin: false, is_demo: true }, 201),
      ),
    )
    vi.stubGlobal('fetch', fetchMock)
    renderButton()

    fireEvent.click(await screen.findByRole('button', { name: /try the demo/i }))

    await waitFor(() =>
      expect(fetchMock).toHaveBeenCalledWith('/api/auth/demo', expect.objectContaining({ method: 'POST' })),
    )
  })
})
