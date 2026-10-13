/**
 * The sign up and sign in box.
 *
 * Built as a real dialog so screen readers get it right
 *   role="dialog" with aria-modal and aria-labelledby
 *   focus goes to the first field when it opens
 *   Escape or a click outside closes it
 *   tabs switch between making an account and signing in
 */

import { useEffect, useRef, useState } from 'react'
import { useLogin, useRegister } from '../api/auth'
import { XIcon } from './Icons'

interface Props {
  open: boolean
  onClose: () => void
  initialTab?: 'register' | 'login'
}

export default function AuthModal({ open, onClose, initialTab = 'register' }: Props) {
  const [tab, setTab] = useState<'register' | 'login'>(initialTab)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)

  const dialogRef = useRef<HTMLDivElement>(null)
  const firstInputRef = useRef<HTMLInputElement>(null)

  const register = useRegister()
  const login = useLogin()

  // Clear the form when it opens or the tab changes
  useEffect(() => {
    if (open) {
      setEmail('')
      setPassword('')
      setError(null)
      setTimeout(() => firstInputRef.current?.focus(), 50)
    }
  }, [open, tab])

  // Escape closes it
  useEffect(() => {
    const handler = (e: KeyboardEvent) => {
      if (e.key === 'Escape' && open) onClose()
    }
    document.addEventListener('keydown', handler)
    return () => document.removeEventListener('keydown', handler)
  }, [open, onClose])

  if (!open) return null

  const isLoading = register.isPending || login.isPending

  const handleSubmit = async (e: React.FormEvent) => {
    e.preventDefault()
    setError(null)

    try {
      if (tab === 'register') {
        await register.mutateAsync({ email, password })
      } else {
        await login.mutateAsync({ email, password })
      }
      onClose()
    } catch (err: unknown) {
      const e = err as { status?: number; code?: string; message?: string }
      if (e.code === 'EMAIL_TAKEN') {
        setError('An account with this email already exists.')
      } else if (e.code === 'INVALID_CREDENTIALS') {
        setError('Invalid email or password.')
      } else {
        setError(e.message ?? 'Something went wrong. Please try again.')
      }
    }
  }

  return (
    // The dark layer behind
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-gray-950/50"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
        className="relative mx-4 w-full max-w-md bg-white shadow-xl"
      >
        <div className="flex items-center justify-between bg-post-600 px-6 py-3.5 text-white">
          <h2 id="auth-modal-title" className="stretch-condensed text-xl font-extrabold uppercase tracking-[0.03em]">
            {tab === 'register' ? 'Create account' : 'Sign in'}
          </h2>
          <button onClick={onClose} className="rounded-sm p-1 hover:bg-white/15" aria-label="Close">
            <XIcon className="h-5 w-5" />
          </button>
        </div>

        <div className="p-6">
        {/* Tabs */}
        <div className="mb-5 flex border-[1.5px] border-gray-900 text-sm font-bold" role="tablist">
          <button
            role="tab"
            aria-selected={tab === 'register'}
            onClick={() => { setTab('register'); setError(null) }}
            className={`flex-1 px-4 py-2 ${tab === 'register' ? 'bg-gray-900 text-white' : 'text-gray-800 hover:bg-gray-100'}`}
          >
            Register
          </button>
          <button
            role="tab"
            aria-selected={tab === 'login'}
            onClick={() => { setTab('login'); setError(null) }}
            className={`flex-1 border-l-[1.5px] border-gray-900 px-4 py-2 ${tab === 'login' ? 'bg-gray-900 text-white' : 'text-gray-800 hover:bg-gray-100'}`}
          >
            Sign in
          </button>
        </div>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div>
            <label htmlFor="auth-email" className="label-form mb-1 block !text-gray-900">
              Email
            </label>
            <input
              ref={firstInputRef}
              id="auth-email"
              type="email"
              autoComplete="email"
              required
              value={email}
              onChange={(e) => setEmail(e.target.value)}
              className="field"
              aria-describedby={error ? 'auth-error' : undefined}
            />
          </div>

          <div>
            <label htmlFor="auth-password" className="label-form mb-1 block !text-gray-900">
              Password {tab === 'register' && <span className="font-normal normal-case tracking-normal text-gray-600">10 characters or more</span>}
            </label>
            <input
              id="auth-password"
              type="password"
              autoComplete={tab === 'register' ? 'new-password' : 'current-password'}
              required
              minLength={tab === 'register' ? 10 : 1}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="field"
            />
          </div>

          {error && (
            <p id="auth-error" role="alert" className="text-sm font-semibold text-post-700">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="btn-primary w-full py-2.5"
          >
            {isLoading ? 'Please wait...' : tab === 'register' ? 'Create account' : 'Sign in'}
          </button>
        </form>
        </div>
      </div>
    </div>
  )
}
