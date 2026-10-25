/**
 * The sign up and sign in form. It sits right in the page, never in a popup.
 *
 * The sign in page uses it, and the resume page shows it under the upload box when a site
 * needs an account. Tabs switch between making an account and signing in, and onDone runs
 * once the server says yes.
 */

import { useEffect, useRef, useState } from 'react'
import { useLogin, useRegister } from '../api/auth'

interface Props {
  initialTab?: 'register' | 'login'
  onDone?: () => void
  /** Put the cursor in the email box right away */
  autoFocus?: boolean
}

export default function AuthForm({ initialTab = 'register', onDone, autoFocus = false }: Props) {
  const [tab, setTab] = useState<'register' | 'login'>(initialTab)
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')
  const [error, setError] = useState<string | null>(null)
  const firstInputRef = useRef<HTMLInputElement>(null)

  const register = useRegister()
  const login = useLogin()

  useEffect(() => {
    if (autoFocus) firstInputRef.current?.focus()
  }, [autoFocus, tab])

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
      onDone?.()
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

  const switchTo = (next: 'register' | 'login') => {
    setTab(next)
    setError(null)
    setPassword('')
  }

  return (
    <div>
      <div className="mb-5 flex overflow-hidden rounded-lg border border-gray-300 text-sm font-bold" role="tablist">
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'register'}
          onClick={() => switchTo('register')}
          className={`flex-1 px-4 py-2 ${tab === 'register' ? 'bg-gray-900 text-white' : 'text-gray-800 hover:bg-gray-100'}`}
        >
          Register
        </button>
        <button
          type="button"
          role="tab"
          aria-selected={tab === 'login'}
          onClick={() => switchTo('login')}
          className={`flex-1 border-l border-gray-300 px-4 py-2 ${tab === 'login' ? 'bg-gray-900 text-white' : 'text-gray-800 hover:bg-gray-100'}`}
        >
          Sign in
        </button>
      </div>

      <form onSubmit={handleSubmit} noValidate className="space-y-4" aria-label={tab === 'register' ? 'Create account' : 'Sign in'}>
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

        <button type="submit" disabled={isLoading} className="btn-primary w-full py-2.5">
          {isLoading ? 'Please wait...' : tab === 'register' ? 'Create account' : 'Sign in'}
        </button>
      </form>
    </div>
  )
}
