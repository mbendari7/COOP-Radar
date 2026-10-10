/**
 * TrackerBoard — Kanban-style board view of saved postings grouped by status.
 * Drag a card to a different column to update the application status.
 *
 * Uses @dnd-kit/core for drag-and-drop with keyboard accessibility built-in.
 */

import {
  DndContext,
  DragOverlay,
  PointerSensor,
  KeyboardSensor,
  useSensor,
  useSensors,
  type DragEndEvent,
} from '@dnd-kit/core'
import { SortableContext, useSortable, verticalListSortingStrategy, sortableKeyboardCoordinates } from '@dnd-kit/sortable'
import { CSS } from '@dnd-kit/utilities'
import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  ALL_STATUSES,
  STATUS_LABELS,
  useUpdateStatus,
  type ApplicationStatus,
  type SavedPostingOut,
} from '../api/saved'

// ── Column colours ────────────────────────────────────────────────────────────

const COLUMN_COLORS: Record<ApplicationStatus, string> = {
  saved:      'border-slate-300 bg-slate-50',
  applying:   'border-yellow-300 bg-yellow-50',
  applied:    'border-blue-300 bg-blue-50',
  interview:  'border-indigo-300 bg-indigo-50',
  offer:      'border-green-300 bg-green-50',
  rejected:   'border-gray-300 bg-gray-50',
  withdrawn:  'border-orange-200 bg-orange-50',
}

const HEADER_COLORS: Record<ApplicationStatus, string> = {
  saved:      'text-slate-600',
  applying:   'text-yellow-700',
  applied:    'text-blue-700',
  interview:  'text-indigo-700',
  offer:      'text-green-700',
  rejected:   'text-gray-600',
  withdrawn:  'text-orange-600',
}

// ── Sortable card ─────────────────────────────────────────────────────────────

function PostingCard({ saved, isDragging }: { saved: SavedPostingOut; isDragging?: boolean }) {
  const { attributes, listeners, setNodeRef, transform, transition } = useSortable({ id: saved.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.4 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="bg-white rounded-lg border border-gray-200 p-3 cursor-grab active:cursor-grabbing shadow-sm hover:shadow-md"
    >
      <Link
        to={`/postings/${saved.posting.id}`}
        className="block text-sm font-medium text-gray-900 hover:text-blue-600 hover:underline leading-snug"
        onClick={(e) => e.stopPropagation()}
      >
        {saved.posting.title}
      </Link>
      <p className="text-xs text-gray-500 mt-0.5">{saved.posting.company}</p>
      {saved.posting.deadline && (
        <p className="text-xs text-gray-400 mt-1">
          Due {new Date(saved.posting.deadline).toLocaleDateString()}
        </p>
      )}
    </div>
  )
}

// ── Board column ──────────────────────────────────────────────────────────────

function BoardColumn({
  status,
  cards,
}: {
  status: ApplicationStatus
  cards: SavedPostingOut[]
}) {
  return (
    <div className={`flex flex-col rounded-lg border-2 ${COLUMN_COLORS[status]} min-h-[200px] p-3 min-w-[200px]`}>
      <div className="flex items-center justify-between mb-3">
        <h3 className={`text-xs font-semibold uppercase tracking-wide ${HEADER_COLORS[status]}`}>
          {STATUS_LABELS[status]}
        </h3>
        <span className="text-xs text-gray-400 bg-white rounded-full px-1.5 py-0.5 border border-gray-200">
          {cards.length}
        </span>
      </div>

      <SortableContext items={cards.map((c) => c.id)} strategy={verticalListSortingStrategy}>
        <div className="flex flex-col gap-2 flex-1">
          {cards.map((saved) => (
            <PostingCard key={saved.id} saved={saved} />
          ))}
          {cards.length === 0 && (
            <div className="flex-1 flex items-center justify-center text-xs text-gray-300 py-4">
              Drop here
            </div>
          )}
        </div>
      </SortableContext>
    </div>
  )
}

// ── Board ─────────────────────────────────────────────────────────────────────

interface Props {
  items: SavedPostingOut[]
}

export default function TrackerBoard({ items }: Props) {
  const updateStatus = useUpdateStatus()
  const [activeId, setActiveId] = useState<string | null>(null)

  const sensors = useSensors(
    useSensor(PointerSensor, { activationConstraint: { distance: 8 } }),
    useSensor(KeyboardSensor, { coordinateGetter: sortableKeyboardCoordinates }),
  )

  // Group cards by status — items with no status go in the "saved" bucket
  const byStatus: Record<ApplicationStatus, SavedPostingOut[]> = {
    saved: [], applying: [], applied: [], interview: [], offer: [], rejected: [], withdrawn: [],
  }
  for (const item of items) {
    const col = item.status ?? 'saved'
    byStatus[col].push(item)
  }

  // Map saved_id → current status for fast lookup during drag
  const idToStatus: Record<string, ApplicationStatus> = {}
  for (const item of items) {
    idToStatus[item.id] = item.status ?? 'saved'
  }

  const activeSaved = activeId ? items.find((i) => i.id === activeId) ?? null : null

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    setActiveId(null)
    if (!over || active.id === over.id) return

    // The `over` id could be another card (sortable) or the column itself.
    // Determine target status: if over is a card id, use its column; otherwise
    // the over id is the column status string.
    const overId = String(over.id)
    const targetStatus: ApplicationStatus = (ALL_STATUSES as string[]).includes(overId)
      ? (overId as ApplicationStatus)
      : (idToStatus[overId] ?? 'saved')

    const currentStatus = idToStatus[String(active.id)]
    if (currentStatus !== targetStatus) {
      updateStatus.mutate({ savedId: String(active.id), status: targetStatus })
    }
  }

  return (
    <DndContext
      sensors={sensors}
      onDragStart={(e) => setActiveId(String(e.active.id))}
      onDragEnd={handleDragEnd}
    >
      <div className="flex gap-4 overflow-x-auto pb-4" role="region" aria-label="Application tracker board">
        {ALL_STATUSES.map((col) => (
          <BoardColumn key={col} status={col} cards={byStatus[col]} />
        ))}
      </div>

      <DragOverlay>
        {activeSaved ? (
          <div className="bg-white rounded-lg border border-blue-300 p-3 shadow-xl rotate-1 w-48">
            <p className="text-sm font-medium text-gray-900">{activeSaved.posting.title}</p>
            <p className="text-xs text-gray-500">{activeSaved.posting.company}</p>
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  )
}
