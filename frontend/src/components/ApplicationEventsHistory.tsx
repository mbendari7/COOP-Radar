/**
 * The dated history of stage changes for one saved job.
 * It folds open under the job in the tracker list.
 */

import { useState } from 'react'
import { STATUS_LABELS, type ApplicationEventOut } from '../api/saved'
import { ChevronDownIcon } from './Icons'
import { formatDate } from '../utils/format'

interface Props {
  events: ApplicationEventOut[]
}

export default function ApplicationEventsHistory({ events }: Props) {
  const [expanded, setExpanded] = useState(false)

  if (events.length === 0) return null

  return (
    <div className="mt-2">
      <button
        type="button"
        onClick={() => setExpanded((v) => !v)}
        className="flex items-center gap-1 text-xs font-semibold text-gray-700 hover:text-gray-900"
        aria-expanded={expanded}
      >
        <ChevronDownIcon className={`h-3.5 w-3.5 transition-transform ${expanded ? '' : '-rotate-90'}`} />
        {events.length} {events.length === 1 ? 'event' : 'events'}
      </button>

      {expanded && (
        <ol className="mt-2 space-y-2 pl-1">
          {events.map((ev) => (
            <li key={ev.id} className="flex gap-2.5 text-xs text-gray-700">
              <span className="mt-1 h-2 w-2 shrink-0 rounded-full border-[1.5px] border-air-700" aria-hidden="true" />
              <div>
                <div className="flex items-center gap-2">
                  <span className="font-bold text-gray-900">
                    {STATUS_LABELS[ev.status]}
                  </span>
                  {ev.event_date && (
                    <span className="text-gray-600">on {ev.event_date}</span>
                  )}
                  <span className="text-gray-400">·</span>
                  <span className="text-gray-600">{formatDate(ev.created_at)}</span>
                </div>
                {ev.notes && (
                  <p className="mt-0.5 text-gray-700">{ev.notes}</p>
                )}
              </div>
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
