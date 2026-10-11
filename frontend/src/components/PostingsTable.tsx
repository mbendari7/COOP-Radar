/**
 * PostingsTable — TanStack Table in manual mode.
 *
 * "Manual" means sorting/filtering/pagination all happen server-side.
 * This component just renders what the API returns and reports user
 * interactions (column header clicks) back to the parent via callbacks.
 *
 * Below the `md` breakpoint we switch to PostingCard list instead of a table
 * so the content is usable on mobile without horizontal scrolling.
 */

import {
  createColumnHelper,
  flexRender,
  getCoreRowModel,
  useReactTable,
  type SortingState,
} from '@tanstack/react-table'
import { useNavigate } from 'react-router-dom'
import type { PostingListItem, SortField, SortOrder } from '../api/postings'
import BookmarkButton from './BookmarkButton'
import PostingCard from './PostingCard'
import LiveBadge from './LiveBadge'
import { formatDate, formatLocation, workModeLabel } from '../utils/format'

const col = createColumnHelper<PostingListItem>()

// Column definitions — id matches the sort field names the API accepts
const columns = [
  col.accessor('title', {
    id: 'title',
    header: 'Role',
    cell: (info) => (
      <span className="font-medium text-gray-900">
        {info.getValue()}
        {info.row.original.source_id && <LiveBadge />}
      </span>
    ),
  }),
  col.accessor('company', {
    id: 'company',
    header: 'Company',
  }),
  col.accessor('city', {
    id: 'city',
    header: 'Location',
    cell: (info) => formatLocation(info.getValue(), info.row.original.province),
    enableSorting: false,
  }),
  col.accessor('work_mode', {
    id: 'work_mode',
    header: 'Mode',
    cell: (info) => workModeLabel(info.getValue()),
    enableSorting: false,
  }),
  col.accessor('term', {
    id: 'term',
    header: 'Term',
    enableSorting: false,
  }),
  col.accessor('duration_months', {
    id: 'duration_months',
    header: 'Length',
    cell: (info) => `${info.getValue()} mo`,
    enableSorting: false,
  }),
  col.accessor('deadline', {
    id: 'deadline',
    header: 'Deadline',
    cell: (info) => formatDate(info.getValue()),
  }),
  col.accessor('posted_at', {
    id: 'posted_at',
    header: 'Posted',
    cell: (info) => formatDate(info.getValue()),
  }),
]

// Sortable column IDs — only these trigger a sort change callback
const SORTABLE: Set<string> = new Set(['title', 'company', 'deadline', 'posted_at'])

interface Props {
  data: PostingListItem[]
  isLoading: boolean
  isError: boolean
  onRetry: () => void
  sort: SortField
  order: SortOrder
  onSortChange: (field: SortField, order: SortOrder) => void
  showBookmarks?: boolean
}

export default function PostingsTable({
  data,
  isLoading,
  isError,
  onRetry,
  sort,
  order,
  onSortChange,
  showBookmarks = false,
}: Props) {
  const navigate = useNavigate()

  // TanStack Table needs a SortingState array even though we're in manual mode.
  // We derive it from the current sort/order URL params.
  const sorting: SortingState = [{ id: sort, desc: order === 'desc' }]

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    // Manual mode — we handle sorting server-side, not in the table itself
    manualSorting: true,
    manualFiltering: true,
    manualPagination: true,
    getCoreRowModel: getCoreRowModel(),
    onSortingChange: (updater) => {
      // TanStack Table calls this when a header is clicked
      const next = typeof updater === 'function' ? updater(sorting) : updater
      if (next.length > 0) {
        const { id, desc } = next[0]
        if (SORTABLE.has(id)) {
          onSortChange(id as SortField, desc ? 'desc' : 'asc')
        }
      }
    },
  })

  // ── Error state ─────────────────────────────────────────────────────────────
  if (isError) {
    return (
      <div className="rounded-lg border border-red-200 bg-red-50 p-8 text-center">
        <p className="text-red-700 font-medium">Something went wrong loading postings.</p>
        <button
          onClick={onRetry}
          className="mt-3 px-4 py-2 bg-red-600 text-white text-sm rounded hover:bg-red-700 focus:outline-none focus:ring-2 focus:ring-red-500 focus:ring-offset-2"
        >
          Try again
        </button>
      </div>
    )
  }

  // ── Mobile card layout (<md) ────────────────────────────────────────────────
  if (!isLoading && data.length === 0) {
    return (
      <div className="rounded-lg border border-dashed border-gray-300 bg-white p-12 text-center">
        <p className="text-gray-500">No postings match — clear filters</p>
      </div>
    )
  }

  return (
    <>
      {/* Mobile cards */}
      <div className="md:hidden space-y-3">
        {isLoading
          ? Array.from({ length: 5 }).map((_, i) => <SkeletonCard key={i} />)
          : data.map((posting) => (
              <PostingCard key={posting.id} posting={posting} showBookmark={showBookmarks} />
            ))
        }
      </div>

      {/* Desktop table */}
      <div className="hidden md:block overflow-x-auto rounded-lg border border-gray-200 bg-white">
        <table className="w-full text-sm" role="table" aria-label="Co-op postings">
          <thead className="bg-gray-50 border-b border-gray-200">
            {table.getHeaderGroups().map((headerGroup) => (
              <tr key={headerGroup.id}>
                {showBookmarks && (
                  <th scope="col" className="px-2 py-3 w-8">
                    <span className="sr-only">Saved</span>
                  </th>
                )}
                {headerGroup.headers.map((header) => {
                  const sortable = SORTABLE.has(header.id)
                  const isSorted = header.id === sort

                  return (
                    <th
                      key={header.id}
                      scope="col"
                      className={`
                        px-4 py-3 text-left text-xs font-semibold text-gray-500 uppercase tracking-wide
                        whitespace-nowrap select-none
                        ${sortable ? 'cursor-pointer hover:text-gray-900' : ''}
                      `}
                      onClick={sortable ? header.column.getToggleSortingHandler() : undefined}
                      onKeyDown={sortable ? (e) => {
                        if (e.key === 'Enter' || e.key === ' ') {
                          e.preventDefault()
                          header.column.getToggleSortingHandler()?.(e)
                        }
                      } : undefined}
                      tabIndex={sortable ? 0 : undefined}
                      aria-sort={
                        !isSorted ? undefined
                          : order === 'asc' ? 'ascending'
                          : 'descending'
                      }
                    >
                      <span className="flex items-center gap-1">
                        {flexRender(header.column.columnDef.header, header.getContext())}
                        {sortable && (
                          <span aria-hidden="true" className="text-gray-300">
                            {isSorted
                              ? order === 'asc' ? '↑' : '↓'
                              : '↕'}
                          </span>
                        )}
                      </span>
                    </th>
                  )
                })}
              </tr>
            ))}
          </thead>

          <tbody className="divide-y divide-gray-100">
            {isLoading
              ? Array.from({ length: 8 }).map((_, i) => <SkeletonRow key={i} colCount={columns.length} />)
              : table.getRowModel().rows.map((row) => (
                  <tr
                    key={row.id}
                    onClick={() => navigate(`/postings/${row.original.id}`)}
                    onKeyDown={(e) => {
                      if (e.key === 'Enter' || e.key === ' ') {
                        e.preventDefault()
                        navigate(`/postings/${row.original.id}`)
                      }
                    }}
                    tabIndex={0}
                    className="hover:bg-blue-50 cursor-pointer focus:outline-none focus:bg-blue-50 focus:ring-inset focus:ring-2 focus:ring-brand-500"
                    aria-label={`${row.original.title} at ${row.original.company}`}
                  >
                    {/* Same position as the "Saved" header cell: first */}
                    {showBookmarks && (
                      <td
                        className="px-2 py-3"
                        onClick={(e) => e.stopPropagation()}
                      >
                        <BookmarkButton
                          postingId={row.original.id}
                          isSaved={row.original.is_saved === true}
                        />
                      </td>
                    )}
                    {row.getVisibleCells().map((cell) => (
                      <td key={cell.id} className="px-4 py-3 text-gray-700 whitespace-nowrap">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))
            }
          </tbody>
        </table>
      </div>
    </>
  )
}

// ── Skeletons ─────────────────────────────────────────────────────────────────

function SkeletonRow({ colCount }: { colCount: number }) {
  return (
    <tr>
      {Array.from({ length: colCount }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 bg-gray-200 rounded animate-pulse" style={{ width: `${50 + (i * 17) % 40}%` }} />
        </td>
      ))}
    </tr>
  )
}

function SkeletonCard() {
  return (
    <div className="bg-white rounded-lg border border-gray-200 p-4 space-y-2 animate-pulse">
      <div className="h-4 bg-gray-200 rounded w-3/4" />
      <div className="h-3 bg-gray-200 rounded w-1/2" />
      <div className="h-3 bg-gray-200 rounded w-2/3" />
    </div>
  )
}
