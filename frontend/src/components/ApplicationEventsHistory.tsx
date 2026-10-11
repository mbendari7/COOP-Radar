/**
 * ApplicationEventsHistory — timestamped status change timeline for a saved posting.
 * Rendered as a collapsible section inside a saved posting card/row.
 */

import { useState } from 'react'
import { STATUS_LABELS, type ApplicationEventOut } from '../api/saved'
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
        className="text-xs text-gray-500 hover:text-gray-600 flex items-center gap-1"
        aria-expanded={expanded}
      >
        <span>{expanded ? '▾' : '▸'}</span>
        {events.length} {events.length === 1 ? 'event' : 'events'}
      </button>

      {expanded && (
        <ol className="mt-2 space-y-2 border-l-2 border-gray-100 pl-3">
          {events.map((ev) => (
            <li key={ev.id} className="text-xs text-gray-600">
              <div className="flex items-center gap-2">
                <span className="font-medium text-gray-800">
                  {STATUS_LABELS[ev.status]}
                </span>
                {ev.event_date && (
                  <span className="text-gray-500">on {ev.event_date}</span>
                )}
                <span className="text-gray-300">·</span>
                <span className="text-gray-500">{formatDate(ev.created_at)}</span>
              </div>
              {ev.notes && (
                <p className="mt-0.5 text-gray-500 italic">{ev.notes}</p>
              )}
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
