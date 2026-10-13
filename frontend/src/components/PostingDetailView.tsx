/**
 * Everything about one job. It shows up in two places
 *   the panel next to the results on the jobs page (variant "pane")
 *   the job's own page at /postings/:id (variant "page"), which phones always use
 *
 * Under the title sits a ruled row of facts and a bar showing the days left to apply,
 * drawn to scale. Then who the job is for, read from the description, so a student can
 * tell at a glance if it is meant for them.
 */

import { Link } from 'react-router-dom'
import { usePosting, type PostingDetail } from '../api/postings'
import BookmarkButton from './BookmarkButton'
import { ExternalIcon } from './Icons'
import Postmark from './Postmark'
import { postmarkPlace } from './postal'
import { Tag } from './PostingCard'
import RichText from './RichText'
import { FIELD_LABELS, ROLE_LABELS } from './roles'
import { formatDate, formatLocation, parseDay, timeAgo, workModeLabel } from '../utils/format'

const DAY = 86_400_000

export default function PostingDetailView({
  posting, variant,
}: { posting: PostingDetail; variant: 'pane' | 'page' }) {
  const Heading = variant === 'page' ? 'h1' : 'h2'
  const estimatedDeadline = posting.low_confidence_fields?.deadline !== undefined
  const asksFor = posting.fields_of_study.map((f) => FIELD_LABELS[f] ?? f)
  const { place, region } = postmarkPlace(posting)

  return (
    <article aria-label={`${posting.title} at ${posting.company}`}>
      <header className="pb-6">
        <div className="flex items-start justify-between gap-5">
          <div className="min-w-0 flex-1">
            <Heading className="display text-[28px] leading-[1.05] text-gray-900 sm:text-[34px]">{posting.title}</Heading>
            <p className="mt-2 text-lg text-gray-900">{posting.company}</p>
            <p className="text-[15px] text-gray-600">
              {formatLocation(posting.city, posting.province, posting.country)}
              {posting.city !== 'Remote' && <> · {workModeLabel(posting.work_mode)}</>}
            </p>
          </div>
          <Postmark
            key={posting.id}
            place={place}
            region={region}
            date={new Date(posting.posted_at)}
            seed={posting.id}
            tone="post"
            stamp
          />
        </div>

        <div className="mt-5 flex flex-wrap items-center gap-2">
          {posting.source_url && (
            <a href={posting.source_url} target="_blank" rel="noopener noreferrer" className="btn-primary max-w-full whitespace-normal px-5 py-2.5 text-left text-[15px]">
              {posting.source_id ? `Apply on ${posting.company}'s site` : 'View original posting'}
              <ExternalIcon className="h-4 w-4" />
            </a>
          )}
          <span className="inline-flex items-center rounded-sm border-2 border-gray-900 pr-2 text-sm font-bold">
            <BookmarkButton postingId={posting.id} isSaved={posting.is_saved === true} />
            {posting.is_saved ? 'Saved' : 'Save'}
          </span>
          {variant === 'pane' && (
            <Link to={`/postings/${posting.id}`} className="link ml-auto text-sm">
              Open full page
            </Link>
          )}
        </div>
      </header>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-4 border-y-[1.5px] border-gray-900 py-4 sm:grid-cols-3">
        <Fact label="Type" value={ROLE_LABELS[posting.role]} />
        <Fact label="Term" value={posting.term && posting.term !== 'Open' ? posting.term : 'Not stated'} />
        <Fact label="Length" value={`${posting.duration_months} months`} />
        <Fact label="Posted" value={timeAgo(posting.posted_at)} />
        <Fact label="Country" value={posting.country === 'US' ? 'United States' : 'Canada'} />
        <Fact label={estimatedDeadline ? 'Apply by, our guess' : 'Apply by'} value={formatDate(posting.deadline)} />
      </dl>

      <DaysLeft postedAt={posting.posted_at} deadline={posting.deadline} estimated={estimatedDeadline} />

      {(asksFor.length > 0 || posting.grad_years.length > 0) && (
        <section aria-labelledby={`who-${posting.id}`} className="border-t border-gray-200 py-5">
          <h3 id={`who-${posting.id}`} className="label-form !text-gray-900">Who it's for</h3>
          <ul className="mt-2 space-y-1.5 text-[15px] text-gray-900">
            {asksFor.length > 0 && <Bullet>Programs it names: {asksFor.join(', ')}</Bullet>}
            {posting.grad_years.length > 0 && <Bullet>Graduating in {posting.grad_years.join(' or ')}</Bullet>}
          </ul>
          <p className="mt-2 text-xs text-gray-600">Read from the job description. Always check the posting itself.</p>
        </section>
      )}

      {posting.skills.length > 0 && (
        <section aria-labelledby={`skills-${posting.id}`} className="border-t border-gray-200 py-5">
          <h3 id={`skills-${posting.id}`} className="label-form !text-gray-900">Skills it mentions</h3>
          <div className="mt-2.5 flex flex-wrap gap-1.5 text-sm">
            {posting.skills.map((s) => <Tag key={s}>{s}</Tag>)}
          </div>
          <p className="mt-3 text-sm text-gray-700">
            <Link to="/resume" className="link">Match your resume</Link>{' '}
            to see which of these you already have.
          </p>
        </section>
      )}

      <section aria-labelledby={`about-${posting.id}`} className="border-t border-gray-200 py-5">
        <h3 id={`about-${posting.id}`} className="label-form !text-gray-900">About the job</h3>
        <div className="mt-3 max-w-[70ch] text-[15px] leading-relaxed text-gray-800">
          {posting.description ? <RichText text={posting.description} /> : (
            <p className="text-gray-600">The employer's page has the full description.</p>
          )}
        </div>
      </section>
    </article>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="label-form">{label}</dt>
      <dd className="mt-0.5 text-[15px] font-semibold text-gray-900">{value}</dd>
    </div>
  )
}

function Bullet({ children }: { children: React.ReactNode }) {
  return (
    <li className="relative pl-5">
      <span className="absolute left-0 top-[7px] h-2.5 w-2.5 rounded-full border-2 border-air-700" aria-hidden="true" />
      {children}
    </li>
  )
}

/**
 * How long is left to apply, drawn to scale. The whole bar is the time from posting
 * to the deadline and the filled part is what has already gone by.
 */
function DaysLeft({ postedAt, deadline, estimated }: { postedAt: string; deadline: string; estimated: boolean }) {
  const start = new Date(postedAt).getTime()
  const end = parseDay(deadline).getTime() + DAY
  const now = Date.now()
  const left = Math.ceil((end - now) / DAY)
  const gone = end > start ? Math.min(1, Math.max(0, (now - start) / (end - start))) : 1
  const urgent = left <= 7

  let text: string
  if (left <= 0) text = 'The deadline has passed'
  else if (left === 1) text = 'Last day to apply'
  else text = `${left} days left to apply`

  return (
    <div className="py-5">
      <p className="flex items-baseline justify-between gap-3">
        <span className={`stretch-semi text-lg font-extrabold ${urgent ? 'text-post-600' : 'text-gray-900'}`}>{text}</span>
        {estimated && left > 0 && (
          <span className="text-xs text-gray-600">This board gives no deadline, so this is our guess</span>
        )}
      </p>
      <div
        className="mt-2 h-2.5 w-full bg-gray-200"
        role="meter"
        aria-label="Time gone since the job was posted"
        aria-valuemin={0}
        aria-valuemax={100}
        aria-valuenow={Math.round(gone * 100)}
      >
        <div className={`h-full ${urgent ? 'bg-post-600' : 'bg-air-700'}`} style={{ width: `${gone * 100}%` }} />
      </div>
      <p className="mt-1.5 flex justify-between text-xs text-gray-600">
        <span>Posted {formatDate(postedAt)}</span>
        <span>{formatDate(deadline)}</span>
      </p>
    </div>
  )
}

/** The details panel on the jobs page. It loads whichever job is picked. */
export function PostingDetailPane({ id }: { id: string | null }) {
  const { data, isLoading, isError } = usePosting(id ?? undefined)

  if (!id) {
    return (
      <div className="flex h-64 items-center justify-center p-8 text-center text-sm text-gray-600">
        Pick a job on the left to see the details here.
      </div>
    )
  }
  if (isLoading) {
    return (
      <div className="animate-pulse space-y-3 p-7" aria-busy="true">
        <div className="h-8 w-2/3 bg-gray-200" />
        <div className="h-4 w-1/3 bg-gray-200" />
        <div className="h-10 w-56 bg-gray-200" />
        {Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-4 bg-gray-100" />)}
      </div>
    )
  }
  if (isError || !data) {
    return <p className="p-7 text-sm text-gray-700">This job didn't load. It may have just closed.</p>
  }
  return (
    <div className="px-7 pt-7">
      <PostingDetailView posting={data} variant="pane" />
    </div>
  )
}
