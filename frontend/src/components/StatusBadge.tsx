/**
 * StatusBadge — inline select for application status on a saved posting.
 *
 * Renders as a colour-coded badge that doubles as a select dropdown.
 * Calls useUpdateStatus on change and shows a brief disabled state during mutation.
 */

import { ALL_STATUSES, STATUS_LABELS, useUpdateStatus, type ApplicationStatus } from '../api/saved'

interface Props {
  savedId: string
  status: ApplicationStatus | null
  postingTitle: string  // for accessible aria-label
}

// Colour classes for each status
function badgeClass(status: ApplicationStatus | null): string {
  switch (status) {
    case 'saved':      return 'bg-slate-100 text-slate-600'
    case 'applying':   return 'bg-yellow-100 text-yellow-700'
    case 'applied':    return 'bg-blue-100 text-blue-700'
    case 'interview':  return 'bg-indigo-100 text-indigo-700'
    case 'offer':      return 'bg-green-100 text-green-700'
    case 'rejected':   return 'bg-gray-100 text-gray-500'
    case 'withdrawn':  return 'bg-orange-50 text-orange-500'
    default:           return 'bg-gray-50 text-gray-500'
  }
}

export default function StatusBadge({ savedId, status, postingTitle }: Props) {
  const updateStatus = useUpdateStatus()

  const handleChange = (e: React.ChangeEvent<HTMLSelectElement>) => {
    const value = e.target.value
    const newStatus = value === '' ? null : (value as ApplicationStatus)
    updateStatus.mutate({ savedId, status: newStatus })
  }

  return (
    <div className="relative inline-block">
      <select
        value={status ?? ''}
        onChange={handleChange}
        disabled={updateStatus.isPending}
        aria-label={`Application status for ${postingTitle}`}
        className={`
          appearance-none text-xs font-medium px-2 py-1 pr-5 rounded-full cursor-pointer
          focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-1
          disabled:opacity-60 disabled:cursor-wait
          ${badgeClass(status)}
        `}
      >
        <option value="">— No status —</option>
        {ALL_STATUSES.map((s) => (
          <option key={s} value={s}>{STATUS_LABELS[s]}</option>
        ))}
      </select>
      <span className="pointer-events-none absolute inset-y-0 right-1 flex items-center text-current opacity-60" aria-hidden="true">
        ▾
      </span>
    </div>
  )
}
