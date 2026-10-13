/**
 * The cancellation stamp for a tracker stage. Same two ring mark as the job postmark,
 * with the stage name on top and the day it changed underneath, like a letter
 * getting stamped at each post office it passes through.
 */

import { STATUS_LABELS, type ApplicationStatus } from '../api/saved'
import { parseDay } from '../utils/format'

const MONTHS = ['JAN', 'FEB', 'MAR', 'APR', 'MAY', 'JUN', 'JUL', 'AUG', 'SEP', 'OCT', 'NOV', 'DEC']

// Early stages in grey, moving ahead in blue, an offer in postal red
const INK: Record<ApplicationStatus, string> = {
  saved: 'text-gray-600',
  applying: 'text-air-600',
  applied: 'text-air-700',
  interview: 'text-air-900',
  offer: 'text-post-600',
  rejected: 'text-gray-500',
  withdrawn: 'text-gray-500',
}

// Each stage sits at its own small tilt so the stamps look pressed by hand
const TILT: Record<ApplicationStatus, number> = {
  saved: -8, applying: 5, applied: -4, interview: 7, offer: -9, rejected: 4, withdrawn: -6,
}

interface Props {
  status: ApplicationStatus
  /** When it moved to this stage. Leave it out to show a count instead */
  date?: string | null
  /** A number in the middle, used for column heads on the board */
  count?: number
}

export default function StageStamp({ status, date, count }: Props) {
  const d = date ? parseDay(date) : null
  // Column heads have no date of their own so they carry today's, like a stamp set for the day
  const day = d ?? new Date()
  const stampDate = `${String(day.getDate()).padStart(2, '0')} ${MONTHS[day.getMonth()]}`
  const label = count !== undefined
    ? `${STATUS_LABELS[status]}, ${count} job${count === 1 ? '' : 's'}`
    : `${STATUS_LABELS[status]}${d ? ` since ${d.toLocaleDateString('en-CA', { month: 'long', day: 'numeric' })}` : ''}`

  return (
    <span
      role="img"
      aria-label={label}
      title={label}
      className={`inline-flex shrink-0 select-none items-center gap-2 ${INK[status]}`}
    >
      <span
        className="relative inline-flex h-[60px] w-[60px] flex-col items-center justify-center rounded-full border-2 border-current text-center uppercase leading-none"
        style={{ transform: `rotate(${TILT[status]}deg)` }}
      >
        <span className="absolute inset-[4px] rounded-full border border-current opacity-70" aria-hidden="true" />
        <span className="stretch-condensed max-w-[46px] truncate text-[8px] font-bold tracking-[0.04em]" aria-hidden="true">{STATUS_LABELS[status]}</span>
        <span className="stretch-condensed mt-[3px] text-[13px] font-extrabold tracking-tight" aria-hidden="true">
          {stampDate}
        </span>
      </span>
      {/* On the board the count sits next to the stamp */}
      {count !== undefined && (
        <span className="stretch-condensed text-2xl font-extrabold tabular-nums text-gray-900" aria-hidden="true">{count}</span>
      )}
    </span>
  )
}
