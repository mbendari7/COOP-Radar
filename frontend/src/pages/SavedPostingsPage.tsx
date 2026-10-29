/**
 * The tracker at /saved.
 *
 * Two views
 *   List can be filtered by stage and has the stage menu, the history and pages
 *   Board groups jobs into columns by stage and you drag to change the stage
 *
 * It also shows how things are going and the deadlines this week.
 * People who are not signed in get a short note and a link back to the jobs.
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
import StageStamp from '../components/StageStamp'
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

  // The board needs every job so it skips paging
  const { data, isLoading, isError, refetch } = useSavedPostings(
    me
      ? view === 'board'
        ? { page_size: 200 }
        : { status: activeStatus, page }
      : {},
  )

  const unsave = useUnsavePosting()

  if (meLoading) {
    return <div className="flex h-64 items-center justify-center text-gray-600">Loading...</div>
  }

  if (!me) {
    return (
      <div className="mx-auto mt-20 max-w-lg px-4 text-center">
        <h1 className="display mb-3 text-3xl text-gray-900">Tracker</h1>
        <p className="mb-6 text-gray-700">Sign in to see and manage the jobs you saved.</p>
        <Link to="/" className="btn-primary">
          Back to jobs
        </Link>
      </div>
    )
  }

  const statusCounts = data?.status_counts ?? {}

  return (
    <div className="w-full px-4 py-8 lg:px-6">
      {/* Title row */}
      <div className="mb-5 flex flex-wrap items-end justify-between gap-4">
        <h1 className="display text-4xl text-gray-900">Tracker</h1>

        <div className="flex items-center gap-2">
          {/* List or board */}
          <div className="flex overflow-hidden rounded-sm border-[1.5px] border-gray-900 text-sm font-bold" role="group" aria-label="View mode">
            <button
              onClick={() => setView('table')}
              aria-pressed={view === 'table'}
              className={`px-3 py-1.5 ${view === 'table' ? 'bg-gray-900 text-white' : 'bg-white text-gray-800 hover:bg-gray-100'}`}
            >
              List
            </button>
            <button
              onClick={() => setView('board')}
              aria-pressed={view === 'board'}
              className={`border-l-[1.5px] border-gray-900 px-3 py-1.5 ${view === 'board' ? 'bg-gray-900 text-white' : 'bg-white text-gray-800 hover:bg-gray-100'}`}
            >
              Board
            </button>
          </div>

          {/* CSV download */}
          <button onClick={downloadCsv} className="btn-secondary py-1.5" aria-label="Export tracker as CSV">
            Download CSV
          </button>
        </div>
      </div>

      {/* How it is going */}
      {data && (
        <StatsPanel
          totalApplied={data.total_applied}
          totalInterview={data.total_interview}
          totalOffer={data.total_offer}
        />
      )}

      {/* Deadlines this week */}
      {data && data.deadlines_this_week.length > 0 && (
        <DeadlinesPanel deadlines={data.deadlines_this_week} />
      )}

      {/* Board view */}
      {view === 'board' && (
        <>
          {isLoading && (
            <div className="flex h-48 items-center justify-center text-gray-600">Loading...</div>
          )}
          {isError && (
            <p className="text-sm font-semibold text-post-700">Your tracker didn't load. <button onClick={() => refetch()} className="underline">Try again</button></p>
          )}
          {!isLoading && !isError && data && (
            <TrackerBoard items={data.items} />
          )}
        </>
      )}

      {/* List view */}
      {view === 'table' && (
        <>
          {/* Tabs for each stage */}
          <div className="mb-2 flex gap-0 overflow-x-auto scroll-none bg-gray-100" role="tablist">
            {STATUS_TABS.map((tab) => (
              <button
                key={tab.label}
                role="tab"
                aria-selected={activeStatus === tab.value}
                onClick={() => { setActiveStatus(tab.value); setPage(1) }}
                className={`whitespace-nowrap px-3.5 py-2.5 text-sm font-bold transition-colors ${
                  activeStatus === tab.value
                    ? 'bg-post-600 text-white'
                    : 'text-gray-800 hover:bg-gray-200'
                }`}
              >
                {tab.label}
                {tab.value && (statusCounts[tab.value] ?? 0) > 0 && (
                  <span className="ml-1.5 text-xs tabular-nums opacity-80">{statusCounts[tab.value]}</span>
                )}
              </button>
            ))}
          </div>

          {isError && (
            <div className="border-y-[1.5px] border-post-600 p-6 text-center">
              <p className="font-semibold text-post-700">Your saved jobs didn't load.</p>
              <button onClick={() => refetch()} className="btn-primary mt-3">
                Try again
              </button>
            </div>
          )}

          {isLoading && (
            <div className="space-y-3">
              {Array.from({ length: 3 }).map((_, i) => (
                <div key={i} className="h-16 animate-pulse bg-gray-100" />
              ))}
            </div>
          )}

          {!isLoading && !isError && data?.total === 0 && (
            <div className="border-y border-gray-300 px-6 py-12 text-center">
              <p className="display text-2xl text-gray-900">Nothing saved yet</p>
              <p className="mt-1.5 text-gray-700">
                <Link to="/" className="link">Browse jobs</Link> or <Link to="/resume" className="link">match your resume</Link> and save the ones you like.
              </p>
            </div>
          )}

          {!isLoading && !isError && data && data.items.length > 0 && (
            <>
              <div className="border-t border-gray-300">
                {data.items.map((saved) => (
                  <div key={saved.id} className="border-b border-gray-300 py-4">
                    <div className="flex items-start gap-4">
                      <div className="hidden w-[60px] shrink-0 sm:block">
                        {saved.status && <StageStamp status={saved.status} date={saved.last_status_at ?? saved.saved_at} />}
                      </div>
                      <div className="min-w-0 flex-1">
                        <div className="flex items-center gap-2 flex-wrap">
                          <Link
                            to={`/postings/${saved.posting.id}`}
                            className="text-[17px] font-bold text-gray-900 hover:text-air-700 hover:underline"
                          >
                            {saved.posting.title}
                          </Link>
                        </div>
                        <p className="mt-0.5 text-sm text-gray-700">
                          {saved.posting.company} · {formatLocation(saved.posting.city, saved.posting.province)} · {saved.posting.term}
                        </p>
                        <p className="mt-1 text-xs text-gray-600">
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
                <div className="mt-6 flex items-center justify-center gap-3">
                  <button
                    onClick={() => setPage((p) => Math.max(1, p - 1))}
                    disabled={page === 1}
                    className="btn-secondary px-3 py-1.5"
                  >
                    Previous
                  </button>
                  <span className="text-sm text-gray-700">
                    Page {page} of {Math.ceil(data.total / data.page_size)}
                  </span>
                  <button
                    onClick={() => setPage((p) => p + 1)}
                    disabled={page >= Math.ceil(data.total / data.page_size)}
                    className="btn-secondary px-3 py-1.5"
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
