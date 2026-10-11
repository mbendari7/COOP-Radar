/**
 * PostingDetailPage — full detail view for a single posting.
 *
 * The URL is /postings/:id — navigating here from the list preserves the list's
 * URL state so pressing Back restores the exact filtered/sorted view.
 */

import { useNavigate, useParams } from 'react-router-dom'
import { usePosting } from '../api/postings'
import BookmarkButton from '../components/BookmarkButton'
import { SimilarPostings } from '../components/SimilarPostings'
import { formatDate, formatLocation, workModeLabel } from '../utils/format'

export default function PostingDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: posting, isLoading, isError } = usePosting(id)

  // ── Loading ───────────────────────────────────────────────────────────────
  if (isLoading) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8 space-y-4 animate-pulse">
        <div className="h-6 bg-gray-200 rounded w-1/3" />
        <div className="h-8 bg-gray-200 rounded w-2/3" />
        <div className="h-4 bg-gray-200 rounded w-1/4" />
        <div className="mt-6 space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-4 bg-gray-200 rounded" style={{ width: `${60 + i * 5}%` }} />
          ))}
        </div>
      </div>
    )
  }

  // ── Error / 404 ───────────────────────────────────────────────────────────
  if (isError || !posting) {
    return (
      <div className="max-w-3xl mx-auto px-4 py-8 text-center">
        <p className="text-gray-500 mb-4">
          {isError ? 'Something went wrong loading this posting.' : 'Posting not found.'}
        </p>
        <button
          onClick={() => navigate(-1)}
          className="text-brand-600 hover:underline focus:outline-none focus:ring-2 focus:ring-brand-500"
        >
          ← Back to postings
        </button>
      </div>
    )
  }

  // ── Detail view ───────────────────────────────────────────────────────────
  return (
    <div className="max-w-6xl mx-auto px-4 py-8 md:grid md:grid-cols-3 md:gap-8">
      {/* Back link */}
      <button
        onClick={() => navigate(-1)}
        className="text-sm text-brand-600 hover:underline mb-6 focus:outline-none focus:ring-2 focus:ring-brand-500 rounded"
        aria-label="Back to postings list"
      >
        ← Back to postings
      </button>

      <article className="md:col-span-2">
        {/* Title + company */}
        <header className="mb-6 flex items-start justify-between gap-3">
          <div>
            <h1 className="text-2xl font-bold text-gray-900">{posting.title}</h1>
            <p className="text-lg text-gray-600 mt-1">{posting.company}</p>
          </div>
          <BookmarkButton postingId={posting.id} isSaved={posting.is_saved === true} />
        </header>

        {/* Meta grid */}
        <dl className="grid grid-cols-2 sm:grid-cols-3 gap-x-6 gap-y-4 mb-8 text-sm">
          <MetaItem label="Location" value={formatLocation(posting.city, posting.province)} />
          <MetaItem label="Work mode" value={workModeLabel(posting.work_mode)} />
          <MetaItem label="Term" value={posting.term} />
          <MetaItem label="Duration" value={`${posting.duration_months} months`} />
          <MetaItem
            label={posting.low_confidence_fields?.deadline !== undefined ? 'Apply by (estimated)' : 'Deadline'}
            value={formatDate(posting.deadline)}
          />
          <MetaItem label="Posted" value={formatDate(posting.posted_at)} />
        </dl>

        {/* Skills */}
        {posting.skills.length > 0 && (
          <section className="mb-8" aria-labelledby="skills-heading">
            <h2 id="skills-heading" className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
              Required skills
            </h2>
            <ul className="flex flex-wrap gap-2" role="list">
              {posting.skills.map((skill) => (
                <li
                  key={skill}
                  className="px-3 py-1 text-sm bg-blue-50 text-blue-700 rounded-full border border-blue-200"
                >
                  {skill}
                </li>
              ))}
            </ul>
          </section>
        )}

        {/* Description */}
        <section aria-labelledby="desc-heading">
          <h2 id="desc-heading" className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-2">
            Description
          </h2>
          {/* whitespace-pre-line preserves line breaks in the description text */}
          <p className="text-gray-700 leading-relaxed whitespace-pre-line">{posting.description}</p>
        </section>

        {/* Source link — only shown when the URL exists */}
        {posting.source_url && (
          <div className="mt-8">
            <a
              href={posting.source_url}
              target="_blank"
              rel="noopener noreferrer"
              className="
                inline-flex items-center gap-2 px-4 py-2 bg-brand-600 text-white text-sm font-medium rounded-lg
                hover:bg-brand-700 focus:outline-none focus:ring-2 focus:ring-brand-500 focus:ring-offset-2
              "
            >
              {posting.source_id ? `Apply on ${posting.company}'s site` : 'View original posting'}
              <span aria-hidden="true">↗</span>
            </a>
          </div>
        )}
      </article>

      {/* Similar postings sidebar */}
      <aside className="mt-8 md:mt-0" aria-label="Similar postings">
        <h2 className="text-sm font-semibold text-gray-500 uppercase tracking-wide mb-3">
          Similar postings
        </h2>
        <SimilarPostings postingId={id!} />
      </aside>
    </div>
  )
}

function MetaItem({ label, value }: { label: string; value: string }) {
  return (
    <div>
      <dt className="text-xs font-medium text-gray-500 uppercase tracking-wide">{label}</dt>
      <dd className="mt-0.5 text-gray-900 font-medium">{value}</dd>
    </div>
  )
}
