/**
 * DemoBanner — reminds visitors they're in a throwaway demo account.
 */

import { useMe } from '../api/auth'

export default function DemoBanner() {
  const { data: me } = useMe()
  if (!me?.is_demo) return null

  return (
    <div role="status" className="bg-amber-50 border-b border-amber-200 text-amber-900 text-sm">
      <div className="max-w-6xl mx-auto px-4 py-2">
        <strong className="font-semibold">You're exploring a demo account.</strong>{' '}
        It's pre-filled with sample applications and resume matches, and it's deleted after 24 hours.
        Sign out and register to keep your own data.
      </div>
    </div>
  )
}
