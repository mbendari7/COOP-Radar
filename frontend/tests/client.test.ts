/**
 * Tests for apiFetch and toApiError. Every API hook leans on these to show backend errors.
 */

import { afterEach, describe, expect, it, vi } from 'vitest'
import { ApiError, apiFetch, toApiError } from '../src/api/client'

function jsonResponse(status: number, body: unknown): Response {
  return new Response(JSON.stringify(body), {
    status,
    headers: { 'Content-Type': 'application/json' },
  })
}

describe('toApiError', () => {
  it('reads the flat { detail, code } shape', async () => {
    const err = await toApiError(jsonResponse(409, { detail: 'Taken', code: 'EMAIL_TAKEN' }))
    expect(err).toBeInstanceOf(ApiError)
    expect(err.status).toBe(409)
    expect(err.code).toBe('EMAIL_TAKEN')
    expect(err.message).toBe('Taken')
  })

  it('maps FastAPI validation errors to VALIDATION_ERROR', async () => {
    const err = await toApiError(jsonResponse(422, { detail: [{ loc: ['body'], msg: 'bad' }] }))
    expect(err.code).toBe('VALIDATION_ERROR')
  })

  it('falls back to HTTP_<status> for non-JSON bodies', async () => {
    const err = await toApiError(new Response('<html>oops</html>', { status: 502 }))
    expect(err.code).toBe('HTTP_502')
  })
})

describe('apiFetch', () => {
  afterEach(() => vi.unstubAllGlobals())

  it('sends cookies and a JSON body, and parses the response', async () => {
    const fetchMock = vi.fn().mockResolvedValue(jsonResponse(200, { ok: true }))
    vi.stubGlobal('fetch', fetchMock)

    const result = await apiFetch<{ ok: boolean }>('/api/thing', { method: 'POST', json: { a: 1 } })

    expect(result).toEqual({ ok: true })
    const [url, init] = fetchMock.mock.calls[0] as [string, RequestInit]
    expect(url).toBe('/api/thing')
    expect(init.credentials).toBe('include')
    expect(init.body).toBe('{"a":1}')
    expect(init.headers).toEqual({ 'Content-Type': 'application/json' })
  })

  it('returns undefined for 204 No Content', async () => {
    vi.stubGlobal('fetch', vi.fn().mockResolvedValue(new Response(null, { status: 204 })))
    await expect(apiFetch<void>('/api/thing', { method: 'DELETE' })).resolves.toBeUndefined()
  })

  it('throws ApiError on failure', async () => {
    vi.stubGlobal(
      'fetch',
      vi.fn().mockResolvedValue(jsonResponse(404, { detail: 'Nope', code: 'POSTING_NOT_FOUND' })),
    )
    await expect(apiFetch('/api/postings/x')).rejects.toMatchObject({ code: 'POSTING_NOT_FOUND' })
  })
})
