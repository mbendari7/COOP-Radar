/**
 * DeadlinesPanel — shows saved postings whose deadlines fall within the next 7 days.
 * Only shows postings not yet in offer/rejected/withdrawn state.
 */

import { Link } from 'react-router-dom'
import type { DeadlineItem } from '../api/saved'

interface Props {
  deadlines: DeadlineItem[]
}

function formatDeadline(iso: string): string {
  if (!iso) return ''
  const d = new Date(iso)
  const today = new Date()
  const diffDays = Math.ceil((d.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))

  if (diffDays === 0) return 'Today'
  if (diffDays === 1) return 'Tomorrow'
  return `${diffDays} days`
}

function urgencyClass(iso: string): string {
  const d = new Date(iso)
  const today = new Date()
  const diffDays = Math.ceil((d.getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
  if (diffDays <= 1) return 'text-red-600 font-semibold'
  if (diffDays <= 3) return 'text-orange-500 font-medium'
  return 'text-yellow-600'
}

export default function DeadlinesPanel({ deadlines }: Props) {
  if (deadlines.length === 0) return null

  return (
    <div className="mb-6 rounded-lg border border-amber-200 bg-amber-50 px-4 py-3">
      <h2 className="text-sm font-semibold text-amber-800 mb-2">
        Deadlines this week ({deadlines.length})
      </h2>
      <ul className="space-y-1">
        {deadlines.map((d) => (
          <li key={d.saved_id} className="flex items-center justify-between text-sm">
            <Link
              to={`/postings/${d.posting_id}`}
              className="text-gray-800 hover:text-blue-600 hover:underline truncate mr-2"
            >
              {d.title} <span className="text-gray-500">· {d.company}</span>
            </Link>
            <span className={`shrink-0 text-xs ${urgencyClass(d.deadline)}`}>
              {formatDeadline(d.deadline)}
            </span>
          </li>
        ))}
      </ul>
    </div>
  )
}
