/**
 * Turn a temporary guest or demo account into a normal one by adding an email and password.
 * The resume, matches and saved jobs all stay.
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
      className="flex flex-col gap-2 sm:flex-row sm:items-end"
    >
      <label className="flex-1 text-sm">
        <span className="label-form mb-1 block !text-gray-900">Email</span>
        <input
          type="email"
          required
          autoComplete="email"
          value={email}
          onChange={(e) => setEmail(e.target.value)}
          className="field"
        />
      </label>
      <label className="flex-1 text-sm">
        <span className="label-form mb-1 block !text-gray-900">Password <span className="font-normal normal-case tracking-normal text-gray-600">10 characters or more</span></span>
        <input
          type="password"
          required
          minLength={10}
          autoComplete="new-password"
          value={password}
          onChange={(e) => setPassword(e.target.value)}
          className="field"
        />
      </label>
      <button type="submit" disabled={claim.isPending} className="btn-primary">
        {claim.isPending ? 'Saving...' : 'Keep my account'}
      </button>
      {claim.isError && (
        <p role="alert" className="text-sm font-semibold text-post-700 sm:basis-full">
          {claim.error.message || 'Could not save your account.'}
        </p>
      )}
    </form>
  )
}
