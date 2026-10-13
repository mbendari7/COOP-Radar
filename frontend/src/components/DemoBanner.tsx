/**
 * Shows while someone is on a temporary account, from the demo or from uploading without an
 * account. Says it gets deleted after 7 days and offers to keep it with an email and password.
 */

import { useState } from 'react'
import { useMe } from '../api/auth'
import ClaimAccountForm from './ClaimAccountForm'

export default function DemoBanner() {
  const { data: me } = useMe()
  const [open, setOpen] = useState(false)
  if (!me?.is_demo) return null

  return (
    <div role="status" className="border-b-[1.5px] border-gray-900 bg-air-50 text-sm text-gray-900">
      <div className="mx-auto max-w-7xl space-y-2 px-4 py-2">
        <p>
          <strong className="font-bold">You're using a temporary account.</strong>{' '}
          Everything here is private to you and deleted after 7 days.{' '}
          {!open && (
            <button type="button" onClick={() => setOpen(true)} className="link underline">
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
