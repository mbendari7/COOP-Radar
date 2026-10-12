/**
 * ClaimAccountForm — turn a temporary (guest/demo) account into a normal one by adding an
 * email + password. The resume, matches, and saved jobs all stay.
 */

import { useState } from 'react'
import { useClaimAccount } from '../api/auth'

export default function ClaimAccountForm({ onDone }: { onDone?: () => void }) {
  const claim = useClaimAccount()
  const [email, setEmail] = useState('')
  const [password, setPassword] = useState('')

  return (
    <form
      onSubmit={(e) => {
        e.preventDefault()
        claim.mutate({ email, password }, { onSuccess: () => onDone?.() })
      }}
      className="flex flex-col sm:flex-row sm:items-end gap-2"
    >
      <label className="flex-1 text-sm">
        <span className="block text-gray-700 mb-1">Email</span>
        <input
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </label>
      <label className="flex-1 text-sm">
        <span className="block text-gray-700 mb-1">Password <span className="text-gray-500">(10+ characters)</span></span>
        <input
          type="password"
          required
          minLength={10}
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
        />
      </label>
      <button
        type="submit"
        disabled={claim.isPending}
        className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
      >
        {claim.isPending ? 'Saving...' : 'Keep my account'}
      </button>
      {claim.isError && (
        <p role="alert" className="text-sm text-red-600 sm:basis-full">
          {claim.error.message || 'Could not save your account.'}
        </p>
      )}
    </form>
  )
}
