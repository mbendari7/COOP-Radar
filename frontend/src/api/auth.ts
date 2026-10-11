/**
 * TanStack Query hooks for authentication and account management.
 *
 * Every call goes through apiFetch, which sends the HTTP-only session cookie
 * (credentials: 'include') and throws ApiError({ status, code }) on failure.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, apiFetch } from './client'

// ── Types ─────────────────────────────────────────────────────────────────────

export interface UserOut {
  id: string
  email: string
  created_at: string
  is_admin: boolean
  /** Throwaway "Try the demo" account (deleted after 24 hours) */
  is_demo: boolean
}

interface Credentials {
  email: string
  password: string
}

// ── Fetchers ──────────────────────────────────────────────────────────────────

/** Current user, or null when not signed in (a 401 is an expected answer here). */
async function fetchMe(): Promise<UserOut | null> {
  try {
    return await apiFetch<UserOut>('/api/me')
  } catch (err) {
    if (err instanceof ApiError && err.status === 401) return null
    throw err
  }
}

export function changePassword(currentPassword: string, newPassword: string): Promise<void> {
  return apiFetch<void>('/api/me/password', {
    method: 'PATCH',
    json: { current_password: currentPassword, new_password: newPassword },
  })
}

export function deleteAccount(password: string): Promise<void> {
  return apiFetch<void>('/api/me', { method: 'DELETE', json: { password } })
}

// ── Hooks ─────────────────────────────────────────────────────────────────────

/** The signed-in user (null when signed out). retry: false so 401s aren't retried. */
export function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: fetchMe,
    staleTime: 60 * 1000,
    retry: false,
  })
}

/** Register a new account. Refreshes 'me' on success. */
export function useRegister() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Credentials) => apiFetch<UserOut>('/api/auth/register', { method: 'POST', json: body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me'] }),
  })
}

/** Log in. Refreshes 'me' and any per-user data (e.g. is_saved flags) on success. */
export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Credentials) => apiFetch<UserOut>('/api/auth/login', { method: 'POST', json: body }),
    onSuccess: () => qc.invalidateQueries(),
  })
}

/**
 * "Try the demo": the server creates a private, pre-filled demo account and logs into it.
 * Refreshes all cached data so every page reflects the new account.
 */
export function useDemoLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => apiFetch<UserOut>('/api/auth/demo', { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries(),
  })
}

/** Log out. Clears every cached query so no stale user data is shown afterwards. */
export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => apiFetch<void>('/api/auth/logout', { method: 'POST' }),
    // Clear even if the server call failed (e.g. session already expired)
    onSettled: () => qc.clear(),
  })
}
