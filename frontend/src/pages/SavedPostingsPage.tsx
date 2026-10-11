/**
 * SavedPostingsPage — /saved route.
 *
 * Two views:
 *  - Table: filterable by status, with StatusBadge, events history, and pagination
 *  - Board: dnd-kit Kanban grouped by status, drag to change status
 *
 * Also shows stats panel and deadlines-this-week panel.
 * Redirects to home if not authenticated.
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { useMe } from '../api/auth'
import {
  ALL_STATUSES,
  STATUS_LABELS,
  downloadCsv,
  type ApplicationStatus,
  useSavedPostings,
  useUnsavePosting,
} from '../api/saved'
import ApplicationEventsHistory from '../components/ApplicationEventsHistory'
import BookmarkButton from '../components/BookmarkButton'
import DeadlinesPanel from '../components/DeadlinesPanel'
import StatsPanel from '../components/StatsPanel'
import StatusBadge from '../components/StatusBadge'
import TrackerBoard from '../components/TrackerBoard'
import { formatDate, formatLocation } from '../utils/format'

type ViewMode = 'table' | 'board'

const STATUS_TABS: { label: string; value: ApplicationStatus | undefined }[] = [
  { label: 'All', value: undefined },
  ...ALL_STATUSES.map((s) => ({ label: STATUS_LABELS[s], value: s })),
]

export default function SavedPostingsPage() {
  const { data: me, isLoading: meLoading } = useMe()
  const [view, setView] = useState<ViewMode>('table')
  const [activeStatus, setActiveStatus] = useState<ApplicationStatus | undefined>(undefined)
  const [page, setPage] = useState(1)

  // Board needs all items — skip pagination when in board view
  const { data, isLoading, isError, refetch } = useSavedPostings(
    me
      ? view === 'board'
        ? { page_size: 200 }
        : { status: activeStatus, page }
      : {},
  )

  const unsave = useUnsavePosting()

  if (meLoading) {
    return <div className="flex justify-center items-center h-64 text-gray-400">Loading…</div>
  }

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

  return (
    <div className="max-w-6xl mx-auto px-4 py-8">
      {/* Header row */}
      <div className="flex items-center justify-between mb-4 gap-4 flex-wrap">
        <h1 className="text-2xl font-semibold text-gray-900">Saved Postings</h1>

        <div className="flex items-center gap-2">
          {/* View toggle */}
          <div className="flex rounded-lg border border-gray-200 overflow-hidden text-sm" role="group" aria-label="View mode">
            <button
              onClick={() => setView('table')}
              aria-pressed={view === 'table'}
              className={`px-3 py-1.5 ${view === 'table' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
            >
              Table
            </button>
            <button
              onClick={() => setView('board')}
              aria-pressed={view === 'board'}
              className={`px-3 py-1.5 border-l border-gray-200 ${view === 'board' ? 'bg-blue-600 text-white' : 'bg-white text-gray-600 hover:bg-gray-50'}`}
            >
              Board
            </button>
          </div>

          {/* CSV export */}
          <button
            onClick={downloadCsv}
            className="px-3 py-1.5 text-sm border border-gray-300 rounded-lg bg-white text-gray-600 hover:bg-gray-50 flex items-center gap-1"
            aria-label="Export tracker as CSV"
          >
            ↓ CSV
          </button>
        </div>
      </div>

      {/* Stats panel */}
      {data && (
        <StatsPanel
          totalApplied={data.total_applied}
          totalInterview={data.total_interview}
          totalOffer={data.total_offer}
        />
      )}

      {/* Deadlines panel */}
      {data && data.deadlines_this_week.length > 0 && (
        <DeadlinesPanel deadlines={data.deadlines_this_week} />
      )}

      {/* ── Board view ── */}
      {view === 'board' && (
        <>
          {isLoading && (
            <div className="h-48 flex items-center justify-center text-gray-400">Loading…</div>
          )}
          {isError && (
            <p className="text-red-600 text-sm">Failed to load. <button onClick={() => refetch()} className="underline">Retry</button></p>
          )}
          {!isLoading && !isError && data && (
            <TrackerBoard items={data.items} />
          )}
        </>
      )}

      {/* ── Table view ── */}
      {view === 'table' && (
        <>
          {/* Status filter tabs */}
          <div className="flex gap-1 mb-6 border-b border-gray-200 overflow-x-auto" role="tablist">
            {STATUS_TABS.map((tab) => (
              <button
                key={tab.label}
                role="tab"
                aria-selected={activeStatus === tab.value}
                onClick={() => { setActiveStatus(tab.value); setPage(1) }}
                className={`px-3 py-2 text-sm font-medium border-b-2 -mb-px whitespace-nowrap ${
                  activeStatus === tab.value
                    ? 'border-blue-600 text-blue-600'
                    : 'border-transparent text-gray-500 hover:text-gray-700'
                }`}
              >
                {tab.label}
                {tab.value && (statusCounts[tab.value] ?? 0) > 0 && (
                  <span className="ml-1 text-xs text-gray-400">({statusCounts[tab.value]})</span>
                )}
              </button>
            ))}
          </div>

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

          {isLoading && (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-16 bg-gray-100 rounded-lg animate-pulse" />
              ))}
            </div>
          )}

          {!isLoading && !isError && data?.total === 0 && (
            <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
              <p className="text-gray-500">
                You haven't saved any postings yet —{' '}
                <Link to="/" className="text-blue-600 hover:underline">browse postings to get started</Link>.
              </p>
            </div>
          )}

          {!isLoading && !isError && data && data.items.length > 0 && (
            <>
              <div className="space-y-3">
                {data.items.map((saved) => (
                  <div
                    key={saved.id}
                    className="bg-white rounded-lg border border-gray-200 p-4"
                  >
                    <div className="flex items-start justify-between gap-4">
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <Link
                            to={`/postings/${saved.posting.id}`}
                            className="font-semibold text-gray-900 hover:text-blue-600 hover:underline"
                          >
                            {saved.posting.title}
                          </Link>
                        </div>
                        <p className="text-sm text-gray-600 mt-0.5">
                          {saved.posting.company} · {formatLocation(saved.posting.city, saved.posting.province)} · {saved.posting.term}
                        </p>
                        <p className="text-xs text-gray-400 mt-1">
                          Saved {formatDate(saved.saved_at)} · Deadline {formatDate(saved.posting.deadline)}
                          {saved.last_status_at && (
                            <> · Updated {formatDate(saved.last_status_at)}</>
                          )}
                        </p>
                        <ApplicationEventsHistory events={saved.events} />
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
                  </div>
                ))}
              </div>

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
        </>
      )}
    </div>
  )
}
