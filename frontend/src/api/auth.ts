/**
 * TanStack Query hooks for signing in and managing the account.
 *
 * Every call goes through apiFetch, which sends the HTTP only session cookie
 * and throws an ApiError with the status and code when something fails.
 */

import { useMutation, useQuery, useQueryClient } from '@tanstack/react-query'
import { ApiError, apiFetch } from './client'

// Types

export interface UserOut {
  id: string
  email: string
  created_at: string
  is_admin: boolean
  /** A temporary demo or guest account. Deleted after 7 days unless kept with /api/me/claim */
  is_demo: boolean
}

interface Credentials {
  email: string
  password: string
}

// Calls to the server

/** The signed in user, or null when nobody is. A 401 is a normal answer here. */
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

// Hooks

/** The signed in user, or null. retry is off so a 401 is not asked again. */
export function useMe() {
  return useQuery({
    queryKey: ['me'],
    queryFn: fetchMe,
    staleTime: 60 * 1000,
    retry: false,
  })
}

/** Make a new account. Refreshes me when it works. */
export function useRegister() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Credentials) => apiFetch<UserOut>('/api/auth/register', { method: 'POST', json: body }),
    onSuccess: () => qc.invalidateQueries({ queryKey: ['me'] }),
  })
}

/** Sign in. Refreshes me and anything personal like the saved marks when it works. */
export function useLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Credentials) => apiFetch<UserOut>('/api/auth/login', { method: 'POST', json: body }),
    onSuccess: () => qc.invalidateQueries(),
  })
}

/**
 * Try the demo. The server makes a private demo account with sample data and signs into it.
 * Refreshes everything cached so every page shows the new account.
 */
export function useDemoLogin() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => apiFetch<UserOut>('/api/auth/demo', { method: 'POST' }),
    onSuccess: () => qc.invalidateQueries(),
  })
}

/**
 * Start without signing up. The server makes an empty temporary account and signs into it.
 * Used when someone who is not signed in uploads their resume.
 */
export function guestLogin(): Promise<UserOut> {
  return apiFetch<UserOut>('/api/auth/guest', { method: 'POST' })
}

/** Keep a temporary account by adding an email and password. Saved jobs and the resume stay. */
export function useClaimAccount() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: (body: Credentials) => apiFetch<UserOut>('/api/me/claim', { method: 'POST', json: body }),
    onSuccess: (user) => qc.setQueryData(['me'], user),
  })
}

/** Sign out. Clears everything cached so no old personal data shows up after. */
export function useLogout() {
  const qc = useQueryClient()
  return useMutation({
    mutationFn: () => apiFetch<void>('/api/auth/logout', { method: 'POST' }),
    // Clear it even if the server call failed, like when the session already ran out
    onSettled: () => qc.clear(),
  })
}
