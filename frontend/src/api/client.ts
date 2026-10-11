/**
 * Shared fetch helper for every API call.
 *
 * - Always sends cookies (`credentials: 'include'`) so the HTTP-only session works.
 * - Turns error responses into an ApiError carrying the backend's error shape:
 *     { "detail": "Human-readable message", "code": "SNAKE_CASE" }
 *   (FastAPI's 422 validation errors have a list `detail`; those get code VALIDATION_ERROR.)
 */

// Empty = same origin: the Vite dev server proxies /api to the backend.
export const API_BASE: string = import.meta.env.VITE_API_URL ?? ''

export class ApiError extends Error {
  readonly status: number
  readonly code: string

  constructor(status: number, code: string, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
    this.code = code
  }
}

/** Build an ApiError from a failed Response, tolerating any body shape. */
export async function toApiError(res: Response): Promise<ApiError> {
  const body: unknown = await res.json().catch(() => null)
  if (body && typeof body === 'object' && 'detail' in body) {
    const { detail, code } = body as { detail: unknown; code?: unknown }
    if (Array.isArray(detail)) {
      return new ApiError(res.status, 'VALIDATION_ERROR', 'Some fields are invalid.')
    }
    // Older nested shape: { detail: { detail, code } }
    if (detail && typeof detail === 'object') {
      const nested = detail as { detail?: unknown; code?: unknown }
      return new ApiError(res.status, String(nested.code ?? `HTTP_${res.status}`), String(nested.detail ?? ''))
    }
    return new ApiError(res.status, String(code ?? `HTTP_${res.status}`), String(detail))
  }
  return new ApiError(res.status, `HTTP_${res.status}`, `Request failed (${res.status})`)
}

/**
 * fetch() wrapper: prefixes API_BASE, includes cookies, sets the JSON header when a
 * JSON body is given, throws ApiError on non-2xx, and parses JSON (undefined for 204).
 */
export async function apiFetch<T>(
  path: string,
  init: Omit<RequestInit, 'body'> & { json?: unknown; body?: BodyInit } = {},
): Promise<T> {
  const { json, headers, ...rest } = init
  const res = await fetch(`${API_BASE}${path}`, {
    credentials: 'include',
    ...rest,
    headers: json !== undefined ? { 'Content-Type': 'application/json', ...headers } : headers,
    body: json !== undefined ? JSON.stringify(json) : init.body,
  })
  if (!res.ok) throw await toApiError(res)
  if (res.status === 204) return undefined as T
  return (await res.json()) as T
}
