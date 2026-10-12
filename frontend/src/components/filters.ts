/** Job filter values shared by FilterBar, ActiveFilterChips and the jobs page. */

import type { CategoryKey, WorkMode } from '../api/postings'

export const WORK_MODES: WorkMode[] = ['onsite', 'hybrid', 'remote']
export const DURATIONS = [4, 8, 12, 16]

export type Level = '' | 'students' | 'all'

export const LEVELS: { value: Level; label: string }[] = [
  { value: '', label: 'Students & entry-level' },
  { value: 'students', label: 'Co-op & intern only' },
  { value: 'all', label: 'All levels' },
]

export const POSTED_WITHIN: { value: number; label: string }[] = [
  { value: 0, label: 'Any time' },
  { value: 1, label: 'Past 24 hours' },
  { value: 3, label: 'Past 3 days' },
  { value: 7, label: 'Past week' },
  { value: 14, label: 'Past 2 weeks' },
  { value: 30, label: 'Past month' },
]

export interface Filters {
  category: CategoryKey[]
  level: Level
  province: string
  city: string
  work_mode: WorkMode | ''
  posted_within: number
  term: string
  duration: number[]
  company: string[]
  skills: string[]
  show_expired: boolean
}

export const EMPTY_FILTERS: Filters = {
  category: [], level: '', province: '', city: '', work_mode: '', posted_within: 0,
  term: '', duration: [], company: [], skills: [], show_expired: false,
}

/** How many filters differ from the defaults (shown on the phone "Filters" button). */
export function countActive(f: Filters): number {
  return (
    f.category.length + f.duration.length + f.company.length + f.skills.length +
    [f.level, f.province, f.city, f.work_mode, f.term].filter(Boolean).length +
    (f.posted_within ? 1 : 0) + (f.show_expired ? 1 : 0)
  )
}
