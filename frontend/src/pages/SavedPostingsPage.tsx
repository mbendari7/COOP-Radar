/**
 * SavedPostingsPage — /saved route.
 *
 * Shows a user's bookmarked postings with status badges and filter tabs.
 * Redirects to home (with AuthModal open) if not authenticated.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMe } from '../api/auth'
import { type ApplicationStatus, useSavedPostings, useUnsavePosting } from '../api/saved'
import BookmarkButton from '../components/BookmarkButton'
import StatusBadge from '../components/StatusBadge'
import { formatDate } from '../utils/format'

const STATUS_TABS: { label: string; value: ApplicationStatus | undefined }[] = [
  { label: 'All', value: undefined },
  { label: 'Applied', value: 'applied' },
  { label: 'Interviewing', value: 'interviewing' },
  { label: 'Offer', value: 'offer' },
  { label: 'Rejected', value: 'rejected' },
]

export default function SavedPostingsPage() {
  const { data: me, isLoading: meLoading } = useMe()
  const [activeStatus, setActiveStatus] = useState<ApplicationStatus | undefined>(undefined)
  const [page, setPage] = useState(1)

  const { data, isLoading, isError, refetch } = useSavedPostings(
    me ? { status: activeStatus, page } : {},
  )

  const unsave = useUnsavePosting()

  // Show a spinner while checking auth
  if (meLoading) {
    return <div className="flex justify-center items-center h-64 text-gray-400">Loading…</div>
  }

  // Not logged in — prompt to sign in
  if (!me) {
    return (
      <div className="max-w-lg mx-auto mt-20 text-center px-4">
        <h1 className="text-2xl font-semibold text-gray-900 mb-3">Saved Postings</h1>
        <p className="text-gray-500 mb-6">Sign in to see and manage your saved postings.</p>
        <Link
          to="/"
          className="inline-block px-5 py-2 bg-blue-600 text-white rounded-lg text-sm font-medium hover:bg-blue-700"
        >
          Back to postings
        </Link>
      </div>
    )
  }

  const statusCounts = data?.status_counts ?? {}
  const totalSaved = Object.values(statusCounts).reduce((a, b) => a + b, 0)

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      <h1 className="text-2xl font-semibold text-gray-900 mb-2">Saved Postings</h1>

      {/* Status summary row */}
      {data && totalSaved > 0 && (
        <p className="text-sm text-gray-500 mb-4">
          {['applied', 'interviewing', 'offer', 'rejected'].map((s) => (
            <span key={s} className="mr-3">
              <span className="font-medium capitalize text-gray-700">{s.charAt(0).toUpperCase() + s.slice(1)}</span>
              : {statusCounts[s] ?? 0}
            </span>
          ))}
        </p>
      )}

      {/* Status filter tabs */}
      <div className="flex gap-1 mb-6 border-b border-gray-200 overflow-x-auto" role="tablist">
        {STATUS_TABS.map((tab) => (
          <button
            key={tab.label}
            role="tab"
            aria-selected={activeStatus === tab.value}
            onClick={() => { setActiveStatus(tab.value); setPage(1) }}
            className={`px-4 py-2 text-sm font-medium border-b-2 -mb-px whitespace-nowrap ${
              activeStatus === tab.value
                ? 'border-blue-600 text-blue-600'
                : 'border-transparent text-gray-500 hover:text-gray-700'
            }`}
          >
            {tab.label}
            {tab.value && statusCounts[tab.value] != null && (
              <span className="ml-1 text-xs text-gray-400">({statusCounts[tab.value]})</span>
            )}
          </button>
        ))}
      </div>

      {/* Error state */}
      {isError && (
        <div className="rounded-lg border border-red-200 bg-red-50 p-6 text-center">
          <p className="text-red-700">Failed to load saved postings.</p>
          <button
            onClick={() => refetch()}
            className="mt-3 px-4 py-1.5 bg-red-600 text-white text-sm rounded hover:bg-red-700"
          >
            Try again
          </button>
        </div>
      )}

      {/* Loading state */}
      {isLoading && (
        <div className="space-y-3">
          {Array.from({ length: 3 }).map((_, i) => (
            <div key={i} className="h-16 bg-gray-100 rounded-lg animate-pulse" />
          ))}
        </div>
      )}

      {/* Empty state */}
      {!isLoading && !isError && data?.total === 0 && (
        <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
          <p className="text-gray-500">
            You haven't saved any postings yet —{' '}
            <Link to="/" className="text-blue-600 hover:underline">browse postings to get started</Link>.
          </p>
        </div>
      )}

      {/* Saved postings list */}
      {!isLoading && !isError && data && data.items.length > 0 && (
        <>
          <div className="space-y-3">
            {data.items.map((saved) => (
              <div
                key={saved.id}
                className="bg-white rounded-lg border border-gray-200 p-4 flex items-start justify-between gap-4"
              >
                <div className="min-w-0 flex-1">
                  <div className="flex items-center gap-2 flex-wrap">
                    <Link
                      to={`/postings/${saved.posting.id}`}
                      className="font-semibold text-gray-900 hover:text-blue-600 hover:underline truncate"
                    >
                      {saved.posting.title}
                    </Link>
                    {saved.posting.is_saved === false && (
                      <span className="text-xs text-amber-600 bg-amber-50 px-1.5 py-0.5 rounded">Expired</span>
                    )}
                  </div>
                  <p className="text-sm text-gray-600 mt-0.5">
                    {saved.posting.company} · {saved.posting.city}, {saved.posting.province} · {saved.posting.term}
                  </p>
                  <p className="text-xs text-gray-400 mt-1">
                    Saved {formatDate(saved.saved_at)} · Deadline {formatDate(saved.posting.deadline)}
                  </p>
                </div>

                <div className="flex items-center gap-2 shrink-0">
                  <StatusBadge
                    savedId={saved.id}
                    status={saved.status}
                    postingTitle={saved.posting.title}
                  />
                  <BookmarkButton
                    postingId={saved.posting.id}
                    savedId={saved.id}
                    isSaved={true}
                    onUnsaved={() => unsave.mutate(saved.id)}
                  />
                </div>
              </div>
            ))}
          </div>

          {/* Pagination */}
          {data.total > data.page_size && (
            <div className="flex justify-center items-center gap-3 mt-6">
              <button
                onClick={() => setPage((p) => Math.max(1, p - 1))}
                disabled={page === 1}
                className="px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40"
              >
                Previous
              </button>
              <span className="text-sm text-gray-500">
                Page {page} of {Math.ceil(data.total / data.page_size)}
              </span>
              <button
                onClick={() => setPage((p) => p + 1)}
                disabled={page >= Math.ceil(data.total / data.page_size)}
                className="px-3 py-1.5 text-sm border border-gray-300 rounded hover:bg-gray-50 disabled:opacity-40"
              >
                Next
              </button>
            </div>
          )}
        </>
      )}
    </div>
  )
}
