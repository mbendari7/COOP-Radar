/**
 * The application stage of a saved job, as a small menu you can change in place.
 * It saves the new stage right away and goes quiet while it saves.
 */

import { ALL_STATUSES, STATUS_LABELS, useUpdateStatus, type ApplicationStatus } from '../api/saved'

interface Props {
  savedId: string
  status: ApplicationStatus | null
  postingTitle: string  // for the screen reader label
}

function badgeClass(status: ApplicationStatus | null): string {
  switch (status) {
    case 'offer':     return 'border-post-600 bg-post-600 text-white'
    case 'interview': return 'border-air-900 bg-air-900 text-white'
    case 'applied':   return 'border-air-700 bg-air-700 text-white'
    case 'applying':  return 'border-air-700 bg-white text-air-700'
    case 'saved':     return 'border-gray-500 bg-white text-gray-800'
    default:          return 'border-gray-400 bg-white text-gray-600'
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
    <select
      value={status ?? ''}
      onChange={handleChange}
      disabled={updateStatus.isPending}
      aria-label={`Application status for ${postingTitle}`}
      className={`cursor-pointer rounded-sm border-[1.5px] py-1 pl-2 pr-7 text-xs font-bold uppercase tracking-wide disabled:cursor-wait disabled:opacity-60 ${badgeClass(status)}`}
    >
      <option value="">No status</option>
      {ALL_STATUSES.map((s) => (
        <option key={s} value={s}>{STATUS_LABELS[s]}</option>
      ))}
    </select>
  )
}
