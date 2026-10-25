/**
 * One job in the results list. A plain row split from the next by a thin rule.
 * Three short lines and nothing more: the title, then employer and place, then the facts
 * students scan for first. The season and term with its dates and length, the kind of role,
 * and on the right when it was posted. Skills and grad years live on the details panel.
 *
 * On wide screens clicking a row picks it for the details panel next to the list (onSelect).
 * On phones, or when there is no panel, it opens the job's own page.
 * The bookmark saves the job without opening it.
 */

import { useNavigate } from 'react-router-dom'
import type { PostingListItem } from '../api/postings'
import BookmarkButton from './BookmarkButton'
import { ROLE_LABELS, splitViewVisible } from './roles'
import { SEASON_DOT, lengthLabel, termDates, termLabel } from './terms'
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
  const term = termLabel(posting.term)
  const length = lengthLabel(posting.duration_months)
  // The year is already in the term, so Summer 2027 reads May to Aug, not May to Aug 2027
  const year = /\d{4}$/.exec(term)?.[0]
  const rawDates = termDates(posting.season, posting.term, posting.duration_months)
  const dates = year && rawDates.match(/\d{4}/g)?.length === 1 ? rawDates.replace(` ${year}`, '') : rawDates
  const termExtras = [dates, length].filter(Boolean)

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
        selected ? 'xl:bg-air-50 xl:shadow-[inset_3px_0_0_theme(colors.air.700)]' : 'hover:bg-gray-50'
      }`}
      aria-label={`${posting.title} at ${posting.company}`}
    >
      <div className="flex items-start gap-3">
        <div className="min-w-0 flex-1">
          <h3 className={`text-[16px] font-bold leading-snug ${selected ? 'text-gray-900 xl:text-air-700' : 'text-gray-900 group-hover:text-air-700'}`}>
            {posting.title}
          </h3>
          <p className="mt-0.5 truncate text-[14px] text-gray-700">
            <span className="font-semibold text-gray-900">{posting.company}</span>
            <span className="mx-1.5 text-gray-400" aria-hidden="true">·</span>
            {formatLocation(posting.city, posting.province, posting.country)}
            {posting.work_mode !== 'onsite' && posting.city !== 'Remote' && <> · {workModeLabel(posting.work_mode)}</>}
          </p>

          <div className="mt-1.5 flex items-center justify-between gap-3 text-[13px]">
            <p className="flex min-w-0 flex-wrap items-center gap-x-2 gap-y-1">
              {(term || length) && (
                <span className="inline-flex items-center gap-1.5 font-semibold text-gray-900">
                  {posting.season && <span className={`h-2 w-2 shrink-0 rounded-full ${SEASON_DOT[posting.season]}`} aria-hidden="true" />}
                  {term || 'Term not stated'}{' '}
                  {termExtras.length > 0 && (
                    <span className="font-normal text-gray-600">· {termExtras.join(' · ')}</span>
                  )}
                </span>
              )}
              {posting.role !== 'job' && (
                <span className="rounded-full bg-air-50 px-2 py-px font-semibold text-air-800">{ROLE_LABELS[posting.role]}</span>
              )}
              {isNew && <span className="rounded-full bg-post-50 px-2 py-px font-bold text-post-700">New</span>}
            </p>
            <span className="shrink-0 whitespace-nowrap text-gray-500">{timeAgo(posting.posted_at)}</span>
          </div>
        </div>

        {showBookmark && (
          <div className="-mr-1.5 -mt-1 shrink-0">
            <BookmarkButton postingId={posting.id} isSaved={posting.is_saved === true} />
          </div>
        )}
      </div>
    </article>
  )
}

/** A tag for a skill or fact. Square, light and quiet */
export function Tag({
  children, tone = 'plain',
}: { children: React.ReactNode; tone?: 'plain' | 'accent' }) {
  const cls = {
    plain: 'border-gray-200 bg-gray-50 text-gray-800',
    accent: 'border-air-200 bg-air-50 text-air-800',
  }[tone]
  return <span className={`inline-block rounded-full border px-2.5 py-0.5 font-medium ${cls}`}>{children}</span>
}
