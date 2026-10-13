/**
 * The one fetch helper every API call uses.
 *
 * It always sends cookies so the HTTP only session works.
 * It turns error replies into an ApiError with the backend's error shape
 *     { "detail": "Message a person can read", "code": "SNAKE_CASE" }
 * FastAPI's 422 errors have a list in detail and those get the code VALIDATION_ERROR.
 */

// Empty means same origin. The Vite dev server passes /api on to the backend
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

/** Build an ApiError from a failed response, whatever shape the body has. */
export async function toApiError(res: Response): Promise<ApiError> {
  const body: unknown = await res.json().catch(() => null)
  if (body && typeof body === 'object' && 'detail' in body) {
    const { detail, code } = body as { detail: unknown; code?: unknown }
    if (Array.isArray(detail)) {
      return new ApiError(res.status, 'VALIDATION_ERROR', 'Some fields are invalid.')
    }
    // The older nested shape { detail: { detail, code } }
    if (detail && typeof detail === 'object') {
      const nested = detail as { detail?: unknown; code?: unknown }
      return new ApiError(res.status, String(nested.code ?? `HTTP_${res.status}`), String(nested.detail ?? ''))
    }
    return new ApiError(res.status, String(code ?? `HTTP_${res.status}`), String(detail))
  }
  return new ApiError(res.status, `HTTP_${res.status}`, `Request failed (${res.status})`)
}

/**
 * A wrapper around fetch(). Adds API_BASE, sends cookies, sets the JSON header when there
 * is a JSON body, throws ApiError when the answer is not 2xx and reads the JSON. 204 gives undefined.
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
