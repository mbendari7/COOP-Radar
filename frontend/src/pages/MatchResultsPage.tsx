/**
 * MatchResultsPage — /matches
 *
 * Shows:
 * - Upload prompt when no resume stored
 * - Ranked match cards (score badge, one-sentence reason, posting details)
 * - "Ask about this role" ConversationPanel on each card
 */

import ConversationPanel from '../components/ConversationPanel'
import ResumeUploadForm from '../components/ResumeUploadForm'
import { useMatches, type MatchResultOut } from '../api/resume'

function scoreBadgeClass(score: number): string {
  if (score >= 70) return 'bg-green-100 text-green-800 border-green-200'
  if (score >= 40) return 'bg-yellow-100 text-yellow-800 border-yellow-200'
  return 'bg-red-100 text-red-800 border-red-200'
}

function MatchCard({ match }: { match: MatchResultOut }) {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm space-y-3">
      {/* Header row */}
      <div className="flex items-start gap-3">
        {/* Score badge */}
        <span
          className={`shrink-0 inline-flex items-center justify-center w-12 h-12 rounded-lg border text-lg font-bold ${scoreBadgeClass(match.score)}`}
          aria-label={`Match score ${match.score} out of 100`}
        >
          {match.score}
        </span>

        {/* Title + company */}
        <div className="min-w-0">
          <h2 className="text-base font-semibold text-gray-900 leading-snug">{match.title}</h2>
          <p className="text-sm text-gray-600">{match.company}</p>
        </div>
      </div>

      {/* Match reason */}
      <p className="text-sm text-gray-700 italic">"{match.reason}"</p>

      {/* Meta grid */}
      <dl className="grid grid-cols-2 sm:grid-cols-4 gap-x-4 gap-y-1 text-xs text-gray-500">
        <div>
          <dt className="font-medium text-gray-400 uppercase tracking-wide">Location</dt>
          <dd className="text-gray-700">{match.city}, {match.province}</dd>
        </div>
        <div>
          <dt className="font-medium text-gray-400 uppercase tracking-wide">Term</dt>
          <dd className="text-gray-700">{match.term}</dd>
        </div>
        {match.deadline && (
          <div>
            <dt className="font-medium text-gray-400 uppercase tracking-wide">Deadline</dt>
            <dd className="text-gray-700">{match.deadline}</dd>
          </div>
        )}
      </dl>

      {/* Q&A panel */}
      <ConversationPanel
        postingId={match.posting_id}
        postingTitle={match.title}
        company={match.company}
      />
    </div>
  )
}

function SkeletonCard() {
  return (
    <div className="rounded-xl border border-gray-200 bg-white p-5 shadow-sm space-y-3 animate-pulse">
      <div className="flex items-start gap-3">
        <div className="w-12 h-12 rounded-lg bg-gray-200" />
        <div className="flex-1 space-y-2">
          <div className="h-4 bg-gray-200 rounded w-2/3" />
          <div className="h-3 bg-gray-200 rounded w-1/3" />
        </div>
      </div>
      <div className="h-3 bg-gray-200 rounded w-full" />
      <div className="h-3 bg-gray-200 rounded w-4/5" />
    </div>
  )
}

export default function MatchResultsPage() {
  const { data, isLoading } = useMatches()

  const hasResume = Boolean(data?.resume)
  const items = data?.items ?? []

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-6">
      {/* Header */}
      <div>
        <h1 className="text-2xl font-bold text-gray-900">My Matches</h1>
        {hasResume && (
          <p className="text-sm text-gray-500 mt-0.5">
            {items.length} posting{items.length !== 1 ? 's' : ''} matched your resume
          </p>
        )}
      </div>

      {/* Upload / replace section */}
      <section aria-label="Resume upload">
        <ResumeUploadForm showStoredCard={hasResume} />
      </section>

      {/* Loading skeletons */}
      {isLoading && (
        <div className="space-y-4">
          {Array.from({ length: 3 }).map((_, i) => <SkeletonCard key={i} />)}
        </div>
      )}

      {/* No resume prompt */}
      {!isLoading && !hasResume && (
        <p className="text-sm text-gray-500">
          Upload your resume above to see personalised match results.
        </p>
      )}

      {/* Match cards */}
      {!isLoading && hasResume && items.length === 0 && (
        <p className="text-sm text-gray-500">
          No matches found yet. Make sure there are postings with embeddings in the database.
        </p>
      )}

      {!isLoading && items.length > 0 && (
        <ol className="space-y-4" aria-label="Matched postings">
          {items.map((match) => (
            <li key={match.posting_id}>
              <MatchCard match={match} />
            </li>
          ))}
        </ol>
      )}
    </div>
  )
}
