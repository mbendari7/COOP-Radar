/**
 * PostingCard — mobile layout for a single posting row.
 * Shown instead of the table below the `md` breakpoint.
 * Each card is a focusable link so keyboard users can navigate without a mouse.
 */

import { useNavigate } from 'react-router-dom'
import type { PostingListItem } from '../api/postings'
import BookmarkButton from './BookmarkButton'
import LiveBadge from './LiveBadge'
import { formatDate, formatLocation, workModeLabel } from '../utils/format'

interface Props {
  posting: PostingListItem
  showBookmark?: boolean
}

export default function PostingCard({ posting, showBookmark = false }: Props) {
  const navigate = useNavigate()

  return (
    <article
      role="article"
      tabIndex={0}
      onClick={() => navigate(`/postings/${posting.id}`)}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          navigate(`/postings/${posting.id}`)
        }
      }}
      className="
        bg-white rounded-lg border border-gray-200 p-4 cursor-pointer
        hover:border-brand-500 hover:shadow-sm transition-all
        focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2
      "
      aria-label={`${posting.title} at ${posting.company}`}
    >
      <div className="flex items-start justify-between gap-2">
        <div className="min-w-0">
          <p className="font-semibold text-gray-900 truncate">
            {posting.title}
            {posting.source_id && <LiveBadge />}
          </p>
          <p className="text-sm text-gray-600 truncate">{posting.company}</p>
        </div>
        <div className="flex items-center gap-1 shrink-0">
          <span className={`text-xs px-2 py-0.5 rounded-full font-medium ${workModeBadgeClass(posting.work_mode)}`}>
            {workModeLabel(posting.work_mode)}
          </span>
          {showBookmark && (
            <BookmarkButton
              postingId={posting.id}
              isSaved={posting.is_saved === true}
            />
          )}
        </div>
      </div>

      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500">
        <span>{formatLocation(posting.city, posting.province)}</span>
        <span>{posting.term}</span>
        <span>{posting.duration_months} mo</span>
      </div>

      <div className="mt-2 flex flex-wrap gap-x-3 gap-y-1 text-xs text-gray-500">
        <span>Deadline: <span className="font-medium text-gray-700">{formatDate(posting.deadline)}</span></span>
        <span>Posted: {formatDate(posting.posted_at)}</span>
      </div>

      {posting.skills.length > 0 && (
        <div className="mt-2 flex flex-wrap gap-1">
          {posting.skills.slice(0, 5).map((skill) => (
            <span key={skill} className="text-xs bg-blue-50 text-blue-700 px-1.5 py-0.5 rounded">
              {skill}
            </span>
          ))}
          {posting.skills.length > 5 && (
            <span className="text-xs text-gray-500">+{posting.skills.length - 5}</span>
          )}
        </div>
      )}
    </article>
  )
}

function workModeBadgeClass(mode: string): string {
  switch (mode) {
    case 'remote': return 'bg-green-100 text-green-700'
    case 'hybrid': return 'bg-yellow-100 text-yellow-700'
    default:       return 'bg-gray-100 text-gray-600'
  }
}
