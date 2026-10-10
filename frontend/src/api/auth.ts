/**
 * TanStack Query hooks for authentication.
 *
 * All fetch calls include credentials: 'include' so the browser attaches
 * the HttpOnly session cookie automatically.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

// ── Types ─────────────────────────────────────────────────────────────────────

export interface UserOut {
  id: string
  email: string
  created_at: string
  is_admin: boolean
}

// ── Fetchers ──────────────────────────────────────────────────────────────────

async function fetchMe(): Promise<UserOut> {
  const res = await fetch(`${API_BASE}/api/me`, { credentials: 'include' })
  if (res.status === 401) throw new Error('NOT_AUTHENTICATED')
  if (!res.ok) throw new Error(`GET /api/me failed: ${res.status}`)
  return res.json() as Promise<UserOut>
}

async function postRegister(body: { email: string; password: string }): Promise<UserOut> {
  const res = await fetch(`${API_BASE}/api/auth/register`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw Object.assign(new Error(err.detail ?? 'Registration failed'), { status: res.status, code: err.code })
  }
  return res.json() as Promise<UserOut>
}

async function postLogin(body: { email: string; password: string }): Promise<UserOut> {
  const res = await fetch(`${API_BASE}/api/auth/login`, {
    method: 'POST',
    headers: { 'Content-Type': 'application/json' },
    credentials: 'include',
    body: JSON.stringify(body),
  })
  if (!res.ok) {
    const err = await res.json().catch(() => ({}))
    throw Object.assign(new Error(err.detail ?? 'Login failed'), { status: res.status, code: err.code })
  }
  return res.json() as Promise<UserOut>
}

async function postLogout(): Promise<void> {
  await fetch(`${API_BASE}/api/auth/logout`, {
    method: 'POST',
    credentials: 'include',
  })
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

/**
 * Returns the currently authenticated user, or undefined if not logged in.
 * retry: false prevents React Query from retrying 401s endlessly.
 */
export function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: fetchMe,
    staleTime: 60 * 1000,
    retry: false,
  })
}

/** Mutation to register a new account. Invalidates the 'me' query on success. */
export function useRegister() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: postRegister,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me'] }),
  })
}

/** Mutation to log in. Invalidates the 'me' query on success. */
export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: postLogin,
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me'] }),
  })
}

/**
 * Mutation to log out.
 * Clears all cached queries so stale user data isn't shown after logout.
 */
export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: postLogout,
    onSuccess: () => qc.clear(),
  })
}
