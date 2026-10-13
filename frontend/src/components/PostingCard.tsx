/**
 * One job in the results list. A plain row split from the next by a thin rule, with the
 * job's postmark on the right showing where it is and the day it was posted.
 *
 * On wide screens clicking a row picks it for the details panel next to the list (onSelect).
 * On phones, or when there is no panel, it opens the job's own page.
 * The bookmark saves the job without opening it.
 */

import { useNavigate } from 'react-router-dom'
import type { PostingListItem } from '../api/postings'
import BookmarkButton from './BookmarkButton'
import Postmark from './Postmark'
import { postmarkPlace } from './postal'
import { ROLE_LABELS, splitViewVisible } from './roles'
import { formatLocation, timeAgo, workModeLabel } from '../utils/format'

interface Props {
  posting: PostingListItem
  showBookmark?: boolean
  selected?: boolean
  /** Runs instead of opening the job page when the details panel is showing */
  onSelect?: (id: string) => void
}


export default function PostingCard({ posting, showBookmark = false, selected = false, onSelect }: Props) {
  const navigate = useNavigate()
  const open = () => {
    if (onSelect && splitViewVisible()) onSelect(posting.id)
    else navigate(`/postings/${posting.id}`)
  }
  const isNew = Date.now() - new Date(posting.posted_at).getTime() < 3 * 86_400_000
  const { place, region } = postmarkPlace(posting)

  return (
    <article
      tabIndex={0}
      onClick={open}
      onKeyDown={(e) => {
        if (e.key === 'Enter' || e.key === ' ') {
          e.preventDefault()
          open()
        }
      }}
      aria-current={selected ? 'true' : undefined}
      className={`group relative cursor-pointer border-b border-gray-200 px-4 py-3 transition-colors focus:outline-none focus-visible:bg-air-50 sm:px-5 ${
        selected ? 'lg:bg-air-50' : 'hover:bg-gray-50'
      }`}
      aria-label={`${posting.title} at ${posting.company}`}
    >
      <div className="flex items-start gap-4">
        <div className="min-w-0 flex-1">
          <h3 className={`text-[16px] font-bold leading-snug ${selected ? 'text-gray-900 lg:text-air-700' : 'text-gray-900 group-hover:text-air-700'}`}>
            {posting.title}
          </h3>
          <p className="mt-0.5 text-sm text-gray-700">
            <span className="font-semibold text-gray-900">{posting.company}</span>
            <span className="mx-1.5 text-gray-400" aria-hidden="true">·</span>
            {formatLocation(posting.city, posting.province, posting.country)}
            {posting.work_mode !== 'onsite' && posting.city !== 'Remote' && <> ({workModeLabel(posting.work_mode)})</>}
          </p>

          <p className="mt-1.5 flex flex-wrap items-center gap-x-3 gap-y-1 text-[13px]">
            {isNew && <span className="label-form !text-post-600">New</span>}
            {posting.role !== 'job' && <span className="label-form !text-air-700">{ROLE_LABELS[posting.role]}</span>}
            {posting.term && posting.term !== 'Open' && <span className="font-semibold text-gray-800">{posting.term}</span>}
            {posting.grad_years.length > 0 && <span className="text-gray-700">Grads {posting.grad_years.join(', ')}</span>}
            {posting.skills.length > 0 && <span className="text-gray-600">{posting.skills.slice(0, 3).join(' · ')}</span>}
            <span className="text-gray-600">Posted {timeAgo(posting.posted_at)}</span>
          </p>
        </div>

        <div className="flex shrink-0 items-start gap-1">
          <Postmark
            place={place}
            region={region}
            date={new Date(posting.posted_at)}
            seed={posting.id}
            tone={selected ? 'post' : 'air'}
            size="sm"
            stamp={selected}
          />
          {showBookmark && <BookmarkButton postingId={posting.id} isSaved={posting.is_saved === true} />}
        </div>
      </div>
    </article>
  )
}

/** A tag for a skill or fact. Square, light and quiet */
export function Tag({
  children, tone = 'plain',
}: { children: React.ReactNode; tone?: 'plain' | 'accent' }) {
  const cls = {
    plain: 'border-gray-300 bg-white text-gray-800',
    accent: 'border-air-200 bg-air-50 text-air-800',
  }[tone]
  return <span className={`inline-block rounded-sm border px-2 py-0.5 font-medium ${cls}`}>{children}</span>
}
