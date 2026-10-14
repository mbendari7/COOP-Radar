/**
 * The tracker as a board. One ruled column per stage on plain white, each headed by its
 * cancellation stamp with the count inside. Jobs are rows split by thin rules, not boxes.
 * Drag a job to another column to change its stage.
 *
 * Uses @dnd-kit/core for drag and drop, which works with the keyboard too.
 */

import {
  DndContext,
  DragOverlay,
  PointerSensor,
  KeyboardSensor,
  useDroppable,
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
import StageStamp from './StageStamp'
import { parseDay } from '../utils/format'

// One job you can drag

function BoardRow({ saved }: { saved: SavedPostingOut }) {
  const { attributes, listeners, setNodeRef, transform, transition, isDragging } = useSortable({ id: saved.id })

  const style = {
    transform: CSS.Transform.toString(transform),
    transition,
    opacity: isDragging ? 0.35 : 1,
  }

  return (
    <div
      ref={setNodeRef}
      style={style}
      {...attributes}
      {...listeners}
      className="cursor-grab border-b border-gray-200 px-2 py-2.5 transition-colors hover:bg-air-50 active:cursor-grabbing"
    >
      <Link
        to={`/postings/${saved.posting.id}`}
        className="block text-sm font-bold leading-snug text-gray-900 hover:text-air-700 hover:underline"
        onClick={(e) => e.stopPropagation()}
      >
        {saved.posting.title}
      </Link>
      <p className="mt-0.5 text-xs text-gray-700">{saved.posting.company}</p>
      {saved.posting.deadline && (
        <p className="mt-0.5 text-xs text-gray-600">
          Due {parseDay(saved.posting.deadline).toLocaleDateString('en-CA', { month: 'short', day: 'numeric' })}
        </p>
      )}
    </div>
  )
}

// One column

function BoardColumn({
  status,
  cards,
}: {
  status: ApplicationStatus
  cards: SavedPostingOut[]
}) {
  // The column itself is a drop target so empty columns still take jobs
  const { setNodeRef, isOver } = useDroppable({ id: status })
  return (
    <div
      ref={setNodeRef}
      className={`flex min-h-[260px] flex-col border-r border-gray-200 px-2 last:border-r-0 ${isOver ? 'bg-air-50' : ''}`}
    >
      <div className="flex flex-col items-center border-b border-gray-300 pb-3 pt-1">
        <h3 className="sr-only">{STATUS_LABELS[status]}</h3>
        <StageStamp status={status} count={cards.length} />
      </div>

      <SortableContext items={cards.map((c) => c.id)} strategy={verticalListSortingStrategy}>
        <div className="flex flex-1 flex-col">
          {cards.map((saved) => (
            <BoardRow key={saved.id} saved={saved} />
          ))}
          {cards.length === 0 && (
            <p className="py-5 text-center text-xs text-gray-600">Drop here</p>
          )}
        </div>
      </SortableContext>
    </div>
  )
}

// The whole board

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

  // Group jobs by stage. Jobs with no stage go under Saved
  const byStatus: Record<ApplicationStatus, SavedPostingOut[]> = {
    saved: [], applying: [], applied: [], interview: [], offer: [], rejected: [], withdrawn: [],
  }
  for (const item of items) {
    const col = item.status ?? 'saved'
    byStatus[col].push(item)
  }

  // Saved id to current stage so dragging can look it up fast
  const idToStatus: Record<string, ApplicationStatus> = {}
  for (const item of items) {
    idToStatus[item.id] = item.status ?? 'saved'
  }

  const activeSaved = activeId ? items.find((i) => i.id === activeId) ?? null : null

  function handleDragEnd(event: DragEndEvent) {
    const { active, over } = event
    setActiveId(null)
    if (!over || active.id === over.id) return

    // What it was dropped on is either another job or the column itself.
    // If it is a job we use that job's column, otherwise the id is the stage name
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
      <div className="overflow-x-auto pb-4" role="region" aria-label="Application tracker board">
        <div className="grid min-w-[1000px] grid-cols-7 border-t border-gray-300 pt-4">
          {ALL_STATUSES.map((col) => (
            <BoardColumn key={col} status={col} cards={byStatus[col]} />
          ))}
        </div>
      </div>

      <DragOverlay>
        {activeSaved ? (
          <div className="w-44 rotate-2 border-[1.5px] border-gray-900 bg-white px-2 py-2.5 shadow-lg">
            <p className="text-sm font-bold text-gray-900">{activeSaved.posting.title}</p>
            <p className="text-xs text-gray-700">{activeSaved.posting.company}</p>
          </div>
        ) : null}
      </DragOverlay>
    </DndContext>
  )
}
