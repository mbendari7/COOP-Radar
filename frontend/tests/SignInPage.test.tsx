/**
 * Tests for the sign in page that took over from the sign in popup. It signs in right on the
 * page and goes back to where the person came from, but never to another site.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Route, Routes, useLocation } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import SignInPage from '../src/pages/SignInPage'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

function Where() {
  const loc = useLocation()
  return <p data-testid="where">{loc.pathname}{loc.search}</p>
}

function renderAt(url: string) {
  const qc = new QueryClient({ defaultOptions: { queries: { retry: false } } })
  return render(
    <MemoryRouter initialEntries={[url]}>
      <QueryClientProvider client={qc}>
        <Routes>
          <Route path="/sign-in" element={<SignInPage />} />
          <Route path="*" element={<Where />} />
        </Routes>
      </QueryClientProvider>
    </MemoryRouter>,
  )
}

async function signIn() {
  fireEvent.change(screen.getByLabelText('Email'), { target: { value: 'a@b.ca' } })
  fireEvent.change(screen.getByLabelText(/^Password/), { target: { value: 'secret-pass-1' } })
  fireEvent.click(screen.getByRole('button', { name: 'Sign in' }))
}

describe('SignInPage', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('is a page, not a dialog', () => {
    renderAt('/sign-in')
    expect(screen.getByRole('heading', { level: 1, name: 'Sign in' })).toBeInTheDocument()
    expect(screen.queryByRole('dialog')).not.toBeInTheDocument()
  })

  it('goes back to the page in next after signing in', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ id: 'u1', email: 'a@b.ca', is_admin: false, is_demo: false })))
    renderAt('/sign-in?next=%2F%3Fseason%3Dwinter')
    await signIn()
    await waitFor(() => expect(screen.getByTestId('where')).toHaveTextContent('/?season=winter'))
  })

  it('ignores a next link to another site', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(json({ id: 'u1', email: 'a@b.ca', is_admin: false, is_demo: false })))
    renderAt('/sign-in?next=%2F%2Fevil.example')
    await signIn()
    await waitFor(() => expect(screen.getByTestId('where')).toHaveTextContent(/^\/$/))
  })

  it('opens on making an account with tab=register', () => {
    renderAt('/sign-in?tab=register')
    expect(screen.getByRole('tab', { name: 'Register' })).toHaveAttribute('aria-selected', 'true')
  })
})
