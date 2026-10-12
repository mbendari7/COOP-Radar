/**
 * PostingDetailView: everything about one job. Used in two places:
 *  - the right-hand panel next to the results on the jobs page (variant "pane")
 *  - the job's own page, /postings/:id (variant "page"), which phones always use
 *
 * Shows what the description asks for (programs of study, graduation years) above the
 * description itself, so students can see at a glance whether a job is meant for them.
 */

import { Link } from 'react-router-dom'
import { usePosting, type PostingDetail } from '../api/postings'
import BookmarkButton from './BookmarkButton'
import { ExternalIcon } from './Icons'
import { CompanyInitial, Tag } from './PostingCard'
import RichText from './RichText'
import { FIELD_LABELS, ROLE_LABELS } from './roles'
import { formatDate, formatLocation, timeAgo, workModeLabel } from '../utils/format'

export default function PostingDetailView({
  posting, variant,
}: { posting: PostingDetail; variant: 'pane' | 'page' }) {
  const Heading = variant === 'page' ? 'h1' : 'h2'
  const estimatedDeadline = posting.low_confidence_fields?.deadline !== undefined
  const asksFor = posting.fields_of_study.map((f) => FIELD_LABELS[f] ?? f)

  return (
    <article aria-label={`${posting.title} at ${posting.company}`}>
      <header className="border-b border-gray-200 pb-5">
        <div className="flex items-start gap-4">
          <CompanyInitial name={posting.company} size="lg" />
          <div className="min-w-0 flex-1">
            <Heading className="text-xl font-bold leading-tight text-gray-900 sm:text-2xl">{posting.title}</Heading>
            <p className="mt-1 text-gray-800">{posting.company}</p>
            <p className="text-sm text-gray-600">
              {formatLocation(posting.city, posting.province, posting.country)}
              {posting.city !== 'Remote' && <> · {workModeLabel(posting.work_mode)}</>}
            </p>
          </div>
        </div>

        <div className="mt-4 flex flex-wrap items-center gap-2">
          {posting.source_url && (
            <a
              href={posting.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="inline-flex items-center gap-2 rounded-md bg-blue-600 px-4 py-2 text-sm font-semibold text-white hover:bg-blue-700 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
            >
              {posting.source_id ? `Apply on ${posting.company}'s site` : 'View original posting'}
              <ExternalIcon className="h-4 w-4" />
            </a>
          )}
          <span className="rounded-md border border-gray-300">
            <BookmarkButton postingId={posting.id} isSaved={posting.is_saved === true} />
          </span>
          {variant === 'pane' && (
            <Link to={`/postings/${posting.id}`} className="ml-auto text-sm text-blue-700 hover:underline">
              Open full page
            </Link>
          )}
        </div>
      </header>

      <dl className="grid grid-cols-2 gap-x-6 gap-y-3 border-b border-gray-200 py-5 text-sm sm:grid-cols-3">
        <Fact label="Type" value={ROLE_LABELS[posting.role]} />
        <Fact label="Term" value={posting.term && posting.term !== 'Open' ? posting.term : 'Not stated'} />
        <Fact label="Length" value={`${posting.duration_months} months`} />
        <Fact label={estimatedDeadline ? 'Apply by (estimated)' : 'Apply by'} value={formatDate(posting.deadline)} />
        <Fact label="Posted" value={timeAgo(posting.posted_at)} />
        <Fact label="Country" value={posting.country === 'US' ? 'United States' : 'Canada'} />
      </dl>

      {(asksFor.length > 0 || posting.grad_years.length > 0) && (
        <section aria-labelledby={`who-${posting.id}`} className="border-b border-gray-200 py-5">
          <h3 id={`who-${posting.id}`} className="font-semibold text-gray-900">Who it's for</h3>
          <ul className="mt-2 space-y-1 text-sm text-gray-700">
            {asksFor.length > 0 && <li>Programs it names: {asksFor.join(', ')}</li>}
            {posting.grad_years.length > 0 && (
              <li>Graduating in {posting.grad_years.join(' or ')}</li>
            )}
          </ul>
          <p className="mt-2 text-xs text-gray-500">Read from the job description. Always check the posting itself.</p>
        </section>
      )}

      {posting.skills.length > 0 && (
        <section aria-labelledby={`skills-${posting.id}`} className="border-b border-gray-200 py-5">
          <h3 id={`skills-${posting.id}`} className="font-semibold text-gray-900">Skills it mentions</h3>
          <div className="mt-2 flex flex-wrap gap-1.5 text-sm">
            {posting.skills.map((s) => <Tag key={s}>{s}</Tag>)}
          </div>
          <p className="mt-3 text-sm text-gray-600">
            <Link to="/resume" className="font-medium text-blue-700 hover:underline">Match your resume</Link>{' '}
            to see which of these you already have.
          </p>
        </section>
      )}

      <section aria-labelledby={`about-${posting.id}`} className="py-5">
        <h3 id={`about-${posting.id}`} className="font-semibold text-gray-900">About the job</h3>
        <div className="mt-2 text-[15px] leading-relaxed text-gray-800">
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
      <dt className="text-gray-500">{label}</dt>
      <dd className="font-medium text-gray-900">{value}</dd>
    </div>
  )
}

/** The details panel on the jobs page: loads the selected job. */
export function PostingDetailPane({ id }: { id: string | null }) {
  const { data, isLoading, isError } = usePosting(id ?? undefined)

  if (!id) {
    return (
      <div className="flex h-64 items-center justify-center p-8 text-center text-sm text-gray-500">
        Pick a job on the left to see the details here.
      </div>
    )
  }
  if (isLoading) {
    return (
      <div className="space-y-3 p-6 animate-pulse" aria-busy="true">
        <div className="h-7 w-2/3 rounded bg-gray-200" />
        <div className="h-4 w-1/3 rounded bg-gray-200" />
        <div className="h-9 w-48 rounded bg-gray-200" />
        {Array.from({ length: 8 }).map((_, i) => <div key={i} className="h-4 rounded bg-gray-100" />)}
      </div>
    )
  }
  if (isError || !data) {
    return <p className="p-6 text-sm text-gray-600">This job didn't load. It may have just closed.</p>
  }
  return (
    <div className="px-6 pt-5">
      <PostingDetailView posting={data} variant="pane" />
    </div>
  )
}
