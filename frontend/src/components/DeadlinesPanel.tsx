/**
 * Saved jobs whose deadline lands in the next 7 days.
 * Jobs already at offer, rejected or withdrawn are left out.
 */

import { Link } from 'react-router-dom'
import type { DeadlineItem } from '../api/saved'
import { parseDay } from '../utils/format'

interface Props {
  deadlines: DeadlineItem[]
}

function daysUntil(iso: string): number {
  const today = new Date()
  today.setHours(0, 0, 0, 0)
  return Math.round((parseDay(iso).getTime() - today.getTime()) / (1000 * 60 * 60 * 24))
}

function formatDeadline(iso: string): string {
  if (!iso) return ''
  const days = daysUntil(iso)
  if (days <= 0) return 'Today'
  if (days === 1) return 'Tomorrow'
  return `${days} days`
}

export default function DeadlinesPanel({ deadlines }: Props) {
  if (deadlines.length === 0) return null

  return (
    <section aria-labelledby="deadlines-title" className="mb-8 border-t-4 border-post-600">
      <h2 id="deadlines-title" className="label-form !text-post-700 pt-2.5">
        Deadlines this week ({deadlines.length})
      </h2>
      <ul className="mt-1 divide-y divide-gray-200">
        {deadlines.map((d) => (
          <li key={d.saved_id} className="flex items-center justify-between gap-3 py-2 text-sm">
            <Link to={`/postings/${d.posting_id}`} className="mr-2 truncate text-gray-900 hover:text-air-700 hover:underline">
              <span className="font-semibold">{d.title}</span> <span className="text-gray-600">· {d.company}</span>
            </Link>
            <span className={`shrink-0 text-xs font-bold uppercase ${daysUntil(d.deadline) <= 2 ? 'text-post-600' : 'text-gray-700'}`}>
              {formatDeadline(d.deadline)}
            </span>
          </li>
        ))}
      </ul>
    </section>
  )
}
