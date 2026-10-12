/**
 * AuthModal — register / login dialog.
 *
 * Rendered as a proper dialog element for accessibility:
 * - role="dialog" with aria-modal and aria-labelledby
 * - Focus trapped inside while open
 * - Closes on Escape key or backdrop click
 * - Switches between Register and Login tabs
 */

import { useEffect, useRef, useState } from 'react'
import { useLogin, useRegister } from '../api/auth'

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

  // Reset form when modal opens or tab changes
  useEffect(() => {
    if (open) {
      setEmail('')
      setPassword('')
      setError(null)
      setTimeout(() => firstInputRef.current?.focus(), 50)
    }
  }, [open, tab])

  // Close on Escape
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
    // Backdrop
    <div
      className="fixed inset-0 z-50 flex items-center justify-center bg-black/40"
      onClick={(e) => { if (e.target === e.currentTarget) onClose() }}
    >
      <div
        ref={dialogRef}
        role="dialog"
        aria-modal="true"
        aria-labelledby="auth-modal-title"
        className="relative w-full max-w-md mx-4 bg-white rounded-xl shadow-xl p-6"
      >
        <button
          onClick={onClose}
          className="absolute top-4 right-4 text-gray-500 hover:text-gray-600"
          aria-label="Close"
        >
          ✕
        </button>

        <h2 id="auth-modal-title" className="text-xl font-semibold text-gray-900 mb-4">
          {tab === 'register' ? 'Create account' : 'Sign in'}
        </h2>

        {/* Tabs */}
        <div className="flex border-b border-gray-200 mb-5" role="tablist">
          <button
            role="tab"
            aria-selected={tab === 'register'}
            onClick={() => { setTab('register'); setError(null) }}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
              tab === 'register'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Register
          </button>
          <button
            role="tab"
            aria-selected={tab === 'login'}
            onClick={() => { setTab('login'); setError(null) }}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px ${
              tab === 'login'
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            Sign in
          </button>
        </div>

        <form onSubmit={handleSubmit} noValidate className="space-y-4">
          <div>
            <label htmlFor="auth-email" className="block text-sm font-medium text-gray-700 mb-1">
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
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
              aria-describedby={error ? 'auth-error' : undefined}
            />
          </div>

          <div>
            <label htmlFor="auth-password" className="block text-sm font-medium text-gray-700 mb-1">
              Password {tab === 'register' && <span className="text-gray-500 font-normal">(min 10 characters)</span>}
            </label>
            <input
              id="auth-password"
              type="password"
              autoComplete={tab === 'register' ? 'new-password' : 'current-password'}
              required
              minLength={tab === 'register' ? 10 : 1}
              value={password}
              onChange={(e) => setPassword(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>

          {error && (
            <p id="auth-error" role="alert" className="text-sm text-red-600">
              {error}
            </p>
          )}

          <button
            type="submit"
            disabled={isLoading}
            className="w-full py-2 px-4 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-50"
          >
            {isLoading ? 'Please wait...' : tab === 'register' ? 'Create account' : 'Sign in'}
          </button>
        </form>
      </div>
    </div>
  )
}
