/**
 * The job results, as a list or a table. TanStack Table runs in manual mode.
 *
 * Manual means sorting, filtering and paging all happen on the server.
 * This just draws what the API sends back and tells the parent when
 * someone clicks a column header.
 *
 * view="cards" is the default on the jobs page and shows the list of rows at every width,
 * with the picked job marked for the details panel beside it. view="table" shows the
 * sortable table on wide screens. Phones always get the list so nothing scrolls sideways.
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
import { ArrowDownIcon, ArrowUpIcon } from './Icons'
import { formatDate, formatLocation, workModeLabel } from '../utils/format'

const col = createColumnHelper<PostingListItem>()

// Columns. Each id matches a sort field the API accepts
const columns = [
  col.accessor('title', {
    id: 'title',
    header: 'Role',
    cell: (info) => (
      <span className="font-semibold text-gray-900">
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
    cell: (info) => formatLocation(info.getValue(), info.row.original.province, info.row.original.country),
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

// Only these columns can be sorted
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
  /** Shows a Clear all filters button when nothing matches */
  onClearFilters?: () => void
  view?: 'cards' | 'table'
  /** The job in the details panel and how to pick another, for the list view */
  selectedId?: string | null
  onSelect?: (id: string) => void
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
  onClearFilters,
  view = 'table',
  selectedId = null,
  onSelect,
}: Props) {
  const navigate = useNavigate()

  // TanStack Table wants a SortingState even in manual mode.
  // We build it from the sort and order in the URL
  const sorting: SortingState = [{ id: sort, desc: order === 'desc' }]

  const table = useReactTable({
    data,
    columns,
    state: { sorting },
    // Manual mode. The server sorts and the table just shows it
    manualSorting: true,
    manualFiltering: true,
    manualPagination: true,
    getCoreRowModel: getCoreRowModel(),
    onSortingChange: (updater) => {
      // TanStack Table calls this when someone clicks a header
      const next = typeof updater === 'function' ? updater(sorting) : updater
      if (next.length > 0) {
        const { id, desc } = next[0]
        if (SORTABLE.has(id)) {
          onSortChange(id as SortField, desc ? 'desc' : 'asc')
        }
      }
    },
  })

  // When loading failed
  if (isError) {
    return (
      <div className="border-y-[1.5px] border-post-600 px-4 py-10 text-center">
        <p className="font-semibold text-post-700">The jobs didn't load. Check your connection and try again.</p>
        <button onClick={onRetry} className="btn-primary mt-4">
          Try again
        </button>
      </div>
    )
  }

  // When nothing matches
  if (!isLoading && data.length === 0) {
    return (
      <div className="px-6 py-14 text-center">
        <p className="display text-2xl text-gray-900">No jobs match these filters</p>
        <p className="mt-1.5 text-sm text-gray-600">Try removing a filter or searching for something broader.</p>
        {onClearFilters && (
          <button type="button" onClick={onClearFilters} className="btn-secondary mt-4">
            Clear all filters
          </button>
        )}
      </div>
    )
  }

  return (
    <>
      {/* The list. Always on phones and at every width in list view */}
      <div className={`${view === 'cards' ? '' : 'md:hidden'} border-t-[1.5px] border-gray-900`}>
        {isLoading
          ? Array.from({ length: 5 }).map((_, i) => <SkeletonCard key={i} />)
          : data.map((posting) => (
              <PostingCard
                key={posting.id}
                posting={posting}
                showBookmark={showBookmarks}
                selected={view === 'cards' && posting.id === selectedId}
                onSelect={view === 'cards' ? onSelect : undefined}
              />
            ))
        }
      </div>

      {/* The table on wide screens */}
      {view === 'table' && (
      <div className="hidden overflow-x-auto border-t-[1.5px] border-gray-900 bg-white md:block">
        <table className="w-full text-sm" role="table" aria-label="Co-op postings">
          <thead className="border-b border-gray-300">
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
                        label-form whitespace-nowrap px-4 py-3 text-left select-none
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
                          <span aria-hidden="true" className={isSorted ? 'text-air-700' : 'text-gray-300'}>
                            {isSorted && order === 'asc' ? <ArrowUpIcon className="h-3.5 w-3.5" /> : <ArrowDownIcon className="h-3.5 w-3.5" />}
                          </span>
                        )}
                      </span>
                    </th>
                  )
                })}
              </tr>
            ))}
          </thead>

          <tbody className="divide-y divide-gray-200">
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
                    className="cursor-pointer hover:bg-air-50 focus:bg-air-50 focus:outline-none"
                    aria-label={`${row.original.title} at ${row.original.company}`}
                  >
                    {/* First, in the same spot as the Saved header */}
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
                      <td key={cell.id} className="whitespace-nowrap px-4 py-3 text-gray-800">
                        {flexRender(cell.column.columnDef.cell, cell.getContext())}
                      </td>
                    ))}
                  </tr>
                ))
            }
          </tbody>
        </table>
      </div>
      )}
    </>
  )
}

// Loading placeholders

function SkeletonRow({ colCount }: { colCount: number }) {
  return (
    <tr>
      {Array.from({ length: colCount }).map((_, i) => (
        <td key={i} className="px-4 py-3">
          <div className="h-4 animate-pulse bg-gray-200" style={{ width: `${50 + (i * 17) % 40}%` }} />
        </td>
      ))}
    </tr>
  )
}

function SkeletonCard() {
  return (
    <div className="flex animate-pulse gap-4 border-b border-gray-200 px-5 py-4">
      <div className="flex-1 space-y-2">
        <div className="h-4 w-3/4 bg-gray-200" />
        <div className="h-3 w-1/2 bg-gray-200" />
        <div className="h-3 w-2/3 bg-gray-100" />
      </div>
      <div className="h-16 w-16 rounded-full border-2 border-gray-200" />
    </div>
  )
}
