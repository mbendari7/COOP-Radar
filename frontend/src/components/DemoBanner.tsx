/**
 * DemoBanner — shown while using a temporary account (the demo, or "upload without an
 * account"). Explains it's deleted after 7 days and offers to keep it with an email + password.
 */

import { useState } from 'react'
import { useMe } from '../api/auth'
import ClaimAccountForm from './ClaimAccountForm'

export default function DemoBanner() {
  const { data: me } = useMe()
  const [open, setOpen] = useState(false)
  if (!me?.is_demo) return null

  return (
    <div role="status" className="bg-amber-50 border-b border-amber-200 text-amber-900 text-sm">
      <div className="max-w-6xl mx-auto px-4 py-2 space-y-2">
        <p>
          <strong className="font-semibold">You're using a temporary account.</strong>{' '}
          Everything here is private to you and deleted after 7 days.{' '}
          {!open && (
            <button
              type="button"
              onClick={() => setOpen(true)}
              className="font-semibold underline hover:text-amber-700"
            >
              Keep my account
            </button>
          )}
        </p>
        {open && (
          <div className="pb-2">
            <ClaimAccountForm onDone={() => setOpen(false)} />
          </div>
        )}
      </div>
    </div>
  )
}
