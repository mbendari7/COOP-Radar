/**
 * Tests for the visitor's own AI key. The key stays in the browser, only goes along as AI
 * headers, and the AI key page checks a key, picks a model and saves it.
 */

import { QueryClient, QueryClientProvider } from '@tanstack/react-query'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { afterEach, describe, expect, it, vi } from 'vitest'
import { aiHeaders, clearAiKey, saveAiKey } from '../src/api/aiKey'
import AiKeyPage from '../src/pages/AiKeyPage'

function json(body: unknown, status = 200): Response {
  return new Response(JSON.stringify(body), { status, headers: { 'Content-Type': 'application/json' } })
}

afterEach(() => {
  clearAiKey()
  vi.unstubAllGlobals()
})

describe('AI key storage', () => {
  it('sends nothing until a key is saved', () => {
    expect(aiHeaders()).toEqual({})
  })

  it('keeps the key for this tab only by default', () => {
    saveAiKey({ provider: 'gemini', apiKey: 'AIza-test', model: 'gemini-flash-latest', remember: false })
    expect(sessionStorage.getItem('coopradar.aiKey')).not.toBeNull()
    expect(localStorage.getItem('coopradar.aiKey')).toBeNull()
    expect(aiHeaders()).toEqual({
      'X-AI-Provider': 'gemini', 'X-AI-Key': 'AIza-test', 'X-AI-Model': 'gemini-flash-latest',
    })
  })

  it('remembers the key on this device when asked, and forgets it on remove', () => {
    saveAiKey({ provider: 'openai', apiKey: 'sk-test', model: 'gpt-5', remember: true })
    expect(localStorage.getItem('coopradar.aiKey')).not.toBeNull()
    clearAiKey()
    expect(aiHeaders()).toEqual({})
  })
})

describe('AiKeyPage', () => {
  it('checks a key, pre-selects the recommended model, and saves it', async () => {
    const fetchMock = vi.fn((url: string, _init?: RequestInit) =>
      Promise.resolve(
        url === '/api/ai/check'
          ? json({
              provider: 'gemini',
              models: [
                { id: 'gemini-2.5-pro', label: 'Gemini 2.5 Pro' },
                { id: 'gemini-flash-latest', label: 'Gemini Flash' },
              ],
              recommended: 'gemini-flash-latest',
            })
          : json({ demo_enabled: true, server_ai_enabled: false, semantic_search_enabled: false, ai_daily_limit: 20 }),
      ),
    )
    vi.stubGlobal('fetch', fetchMock)

    render(
      <MemoryRouter>
        <QueryClientProvider client={new QueryClient()}>
          <AiKeyPage />
        </QueryClientProvider>
      </MemoryRouter>,
    )

    fireEvent.change(screen.getByLabelText('Gemini API key'), { target: { value: 'AIza-visitor-key' } })
    fireEvent.click(screen.getByRole('button', { name: /check key/i }))

    const select = await screen.findByLabelText(/model/i)
    expect((select as HTMLSelectElement).value).toBe('gemini-flash-latest')

    fireEvent.click(screen.getByRole('button', { name: /use this key/i }))

    await waitFor(() => expect(screen.getByText(/using your gemini key/i)).toBeInTheDocument())
    expect(aiHeaders()['X-AI-Key']).toBe('AIza-visitor-key')
    // The key went to our server only for the check, never in a URL
    const checkCall = fetchMock.mock.calls.find(([url]) => url === '/api/ai/check')!
    expect(JSON.parse(checkCall[1]!.body as string)).toEqual({
      provider: 'gemini', api_key: 'AIza-visitor-key',
    })
  })
})
