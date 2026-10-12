/**
 * PostingCard: one job in the card list (the default view, and the only one on phones).
 * The whole card opens the job; the bookmark button saves it without opening.
 */

import { useNavigate } from 'react-router-dom'
import type { PostingListItem } from '../api/postings'
import BookmarkButton from './BookmarkButton'
import { PinIcon } from './Icons'
import { formatDate, formatLocation, timeAgo, workModeLabel } from '../utils/format'

interface Props {
  posting: PostingListItem
  showBookmark?: boolean
}

export default function PostingCard({ posting, showBookmark = false }: Props) {
  const navigate = useNavigate()
  const open = () => navigate(`/postings/${posting.id}`)

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
      className="group cursor-pointer rounded-lg border border-gray-200 bg-white p-4 sm:p-5 transition-colors hover:border-gray-400 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
      aria-label={`${posting.title} at ${posting.company}`}
    >
      <div className="flex items-start gap-3 sm:gap-4">
        <CompanyInitial name={posting.company} />

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <div className="min-w-0">
              <h3 className="font-semibold text-gray-900 group-hover:text-blue-800 leading-snug">
                {posting.title}
              </h3>
              <p className="mt-0.5 text-sm text-gray-600">
                {posting.company}
                <span className="mx-1.5 text-gray-300" aria-hidden="true">|</span>
                <PinIcon className="mr-0.5 inline h-3.5 w-3.5 -translate-y-px text-gray-400" />
                {formatLocation(posting.city, posting.province)}
              </p>
            </div>
            {showBookmark && (
              <div className="-mr-1.5 -mt-1 shrink-0">
                <BookmarkButton postingId={posting.id} isSaved={posting.is_saved === true} />
              </div>
            )}
          </div>

          <div className="mt-2.5 flex flex-wrap gap-1.5 text-xs">
            <Tag tone={posting.work_mode === 'remote' ? 'accent' : 'plain'}>{workModeLabel(posting.work_mode)}</Tag>
            {posting.term && posting.term !== 'Open' && <Tag>{posting.term}</Tag>}
            <Tag>{posting.duration_months} months</Tag>
          </div>

          {posting.skills.length > 0 && (
            <p className="mt-2.5 text-sm text-gray-600">
              <span className="text-gray-500">Skills: </span>
              {posting.skills.slice(0, 6).join(', ')}
              {posting.skills.length > 6 && <span className="text-gray-500"> and {posting.skills.length - 6} more</span>}
            </p>
          )}

          <p className="mt-2 text-xs text-gray-500">
            Posted {timeAgo(posting.posted_at)}
            <span className="mx-1.5" aria-hidden="true">·</span>
            Apply by {formatDate(posting.deadline)}
          </p>
        </div>
      </div>
    </article>
  )
}

/** A square with the company's first letter, in a colour picked from its name. */
export function CompanyInitial({ name, size = 'md' }: { name: string; size?: 'md' | 'lg' }) {
  const palette = [
    'bg-[#e8efe9] text-[#245840]', 'bg-[#efe9e1] text-[#7a4f24]', 'bg-[#e6ecf2] text-[#2f4e6b]',
    'bg-[#f1e7ea] text-[#7b3346]', 'bg-[#ece9f2] text-[#4e3f73]', 'bg-[#eef0e0] text-[#59612a]',
  ]
  const hash = [...name].reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) >>> 0, 7)
  const dims = size === 'lg' ? 'h-14 w-14 text-xl' : 'h-11 w-11 text-base'
  return (
    <span
      className={`flex shrink-0 items-center justify-center rounded-md font-semibold ${dims} ${palette[hash % palette.length]}`}
      aria-hidden="true"
    >
      {name.replace(/^\W+/, '').charAt(0).toUpperCase() || '?'}
    </span>
  )
}

function Tag({
  children, tone = 'plain', title,
}: { children: React.ReactNode; tone?: 'plain' | 'accent'; title?: string }) {
  const cls = {
    plain: 'bg-gray-100 text-gray-700',
    accent: 'bg-blue-50 text-blue-800',
  }[tone]
  return <span className={`rounded px-2 py-0.5 font-medium ${cls}`} title={title}>{children}</span>
}
