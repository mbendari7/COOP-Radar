/** Job filter values shared by FilterBar, ActiveFilterChips and the jobs page. */

import type { CategoryKey, CountryCode, ProgramKey, Season, WorkMode } from '../api/postings'

export const WORK_MODES: WorkMode[] = ['onsite', 'hybrid', 'remote']
export const DURATIONS = [4, 8, 12, 16]

/** Empty means co-op and internships, the default since that is what most students here want */
export type Level = '' | 'entry' | 'all'

export const LEVELS: { value: Level; label: string; short: string }[] = [
  { value: '', label: 'Co-op & internships', short: 'Co-op & internships' },
  { value: 'entry', label: 'Students & entry-level', short: 'Entry-level too' },
  { value: 'all', label: 'All levels', short: 'All levels' },
]

/** Empty means Canada, the default. US for the US or all for both */
export type CountryChoice = '' | 'US' | 'all'

export const COUNTRY_CHOICES: { value: CountryChoice; label: string }[] = [
  { value: '', label: 'Canada' },
  { value: 'US', label: 'United States' },
  { value: 'all', label: 'Canada and US' },
]

export function countriesFor(choice: CountryChoice): CountryCode[] | undefined {
  if (choice === 'all') return undefined
  return choice === 'US' ? ['US'] : ['CA']
}

/** This year and the next six for the Graduating in menus. */
export function gradYears(now: Date = new Date()): number[] {
  return Array.from({ length: 7 }, (_, i) => now.getFullYear() + i)
}

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
  country: CountryChoice
  program: ProgramKey | ''
  grad_year: number
  province: string
  city: string
  work_mode: WorkMode | ''
  posted_within: number
  term: string
  season: Season[]
  duration: number[]
  company: string[]
  skills: string[]
  show_expired: boolean
}

export const EMPTY_FILTERS: Filters = {
  category: [], level: '', country: '', program: '', grad_year: 0, province: '', city: '',
  work_mode: '', posted_within: 0, term: '', season: [], duration: [], company: [], skills: [],
  show_expired: false,
}

/** How many filters are changed from the defaults. Shown on the All filters button. */
export function countActive(f: Filters): number {
  return (
    f.category.length + f.season.length + f.duration.length + f.company.length + f.skills.length +
    [f.level, f.country, f.program, f.province, f.city, f.work_mode, f.term].filter(Boolean).length +
    (f.grad_year ? 1 : 0) + (f.posted_within ? 1 : 0) + (f.show_expired ? 1 : 0)
  )
}
