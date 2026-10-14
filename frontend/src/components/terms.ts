/**
 * Co-op term seasons and lengths, shared by the job list, details, table and filters.
 * The server reads both from each job (backend/app/ingest/terms.py).
 */

import type { Season } from '../api/postings'

export const SEASONS: { value: Season; label: string; months: string }[] = [
  { value: 'winter', label: 'Winter', months: 'January to April' },
  { value: 'spring', label: 'Spring', months: 'dates vary by school' },
  { value: 'summer', label: 'Summer', months: 'May to August' },
  { value: 'fall', label: 'Fall', months: 'September to December' },
]

/** A small dot so seasons are easy to tell apart when scanning a long list */
export const SEASON_DOT: Record<Season, string> = {
  winter: 'bg-sky-600',
  spring: 'bg-emerald-600',
  summer: 'bg-amber-500',
  fall: 'bg-orange-700',
}

export function seasonLabel(season: Season | null | undefined): string {
  return SEASONS.find((s) => s.value === season)?.label ?? ''
}

/** "4 months", or '' when the job does not say */
export function lengthLabel(months: number | null | undefined): string {
  return months ? `${months} months` : ''
}

/** The term as people say it, or '' when the job gives none. "Open" means it did not say */
export function termLabel(term: string | null | undefined): string {
  return term && term !== 'Open' ? term : ''
}
