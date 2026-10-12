/**
 * PostingCard: one job in the results list, laid out like a job board's list item.
 *
 * On wide screens the jobs page shows the list next to a details panel: clicking a card
 * selects it (onSelect). On phones, or when there's no panel, it opens the job's own page.
 * The bookmark button saves the job without opening it.
 */

import { useNavigate } from 'react-router-dom'
import type { PostingListItem } from '../api/postings'
import BookmarkButton from './BookmarkButton'
import { ROLE_LABELS, splitViewVisible } from './roles'
import { formatLocation, timeAgo, workModeLabel } from '../utils/format'

interface Props {
  posting: PostingListItem
  showBookmark?: boolean
  selected?: boolean
  /** Called instead of opening the job page when the details panel is visible */
  onSelect?: (id: string) => void
}

export default function PostingCard({ posting, showBookmark = false, selected = false, onSelect }: Props) {
  const navigate = useNavigate()
  const open = () => {
    if (onSelect && splitViewVisible()) onSelect(posting.id)
    else navigate(`/postings/${posting.id}`)
  }
  const isNew = Date.now() - new Date(posting.posted_at).getTime() < 3 * 86_400_000

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
      className={`group relative cursor-pointer border bg-white px-4 py-3.5 transition-colors focus:outline-none focus-visible:ring-2 focus-visible:ring-blue-600 sm:rounded-md ${
        selected ? 'border-gray-200 lg:border-blue-600 lg:ring-1 lg:ring-blue-600' : 'border-gray-200 hover:border-gray-400'
      }`}
      aria-label={`${posting.title} at ${posting.company}`}
    >
      <div className="flex items-start gap-3">
        <CompanyInitial name={posting.company} />

        <div className="min-w-0 flex-1">
          <div className="flex items-start justify-between gap-2">
            <h3 className={`text-[15px] font-semibold leading-snug ${selected ? 'text-gray-900 lg:text-blue-800' : 'text-gray-900 group-hover:underline'}`}>
              {posting.title}
            </h3>
            {showBookmark && (
              <div className="-mr-1.5 -mt-1 shrink-0">
                <BookmarkButton postingId={posting.id} isSaved={posting.is_saved === true} />
              </div>
            )}
          </div>
          <p className="text-sm text-gray-800">{posting.company}</p>
          <p className="text-sm text-gray-600">
            {formatLocation(posting.city, posting.province, posting.country)}
            {posting.work_mode !== 'onsite' && posting.city !== 'Remote' && <> ({workModeLabel(posting.work_mode)})</>}
          </p>

          <div className="mt-2 flex flex-wrap gap-1.5 text-xs">
            {posting.role !== 'job' && <Tag tone="accent">{ROLE_LABELS[posting.role]}</Tag>}
            {posting.term && posting.term !== 'Open' && <Tag>{posting.term}</Tag>}
            {posting.grad_years.length > 0 && <Tag>Grads {posting.grad_years.join(', ')}</Tag>}
            {posting.skills.slice(0, 3).map((s) => <Tag key={s}>{s}</Tag>)}
          </div>

          <p className="mt-2 text-xs text-gray-500">
            {isNew && <span className="mr-1.5 font-semibold text-green-700">New</span>}
            Posted {timeAgo(posting.posted_at)}
          </p>
        </div>
      </div>
    </article>
  )
}

/** A square with the company's first letter, in a colour picked from its name. */
export function CompanyInitial({ name, size = 'md' }: { name: string; size?: 'md' | 'lg' }) {
  const palette = [
    'bg-[#e6eef8] text-[#1f4a8f]', 'bg-[#efe9e1] text-[#7a4f24]', 'bg-[#e4f1ea] text-[#24603f]',
    'bg-[#f1e7ea] text-[#7b3346]', 'bg-[#ece9f2] text-[#4e3f73]', 'bg-[#eef0e0] text-[#59612a]',
  ]
  const hash = [...name].reduce((h, ch) => (h * 31 + ch.charCodeAt(0)) >>> 0, 7)
  const dims = size === 'lg' ? 'h-14 w-14 text-xl' : 'h-10 w-10 text-base'
  return (
    <span
      className={`flex shrink-0 items-center justify-center rounded font-bold ${dims} ${palette[hash % palette.length]}`}
      aria-hidden="true"
    >
      {name.replace(/^\W+/, '').charAt(0).toUpperCase() || '?'}
    </span>
  )
}

export function Tag({
  children, tone = 'plain',
}: { children: React.ReactNode; tone?: 'plain' | 'accent' }) {
  const cls = {
    plain: 'bg-gray-100 text-gray-700',
    accent: 'bg-blue-50 text-blue-800 ring-1 ring-inset ring-blue-200',
  }[tone]
  return <span className={`rounded px-1.5 py-0.5 font-medium ${cls}`}>{children}</span>
}
