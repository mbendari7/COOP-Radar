/**
 * Co-op term seasons and lengths, shared by the job list, details, table and filters.
 * The server reads both from each job (backend/app/ingest/terms.py).
 */

import type { Season } from '../api/postings'

export const SEASONS: { value: Season; label: string; months: string; short: string }[] = [
  { value: 'winter', label: 'Winter', months: 'January to April', short: 'Jan to Apr' },
  { value: 'spring', label: 'Spring', months: 'dates vary by school', short: 'varies' },
  { value: 'summer', label: 'Summer', months: 'May to August', short: 'May to Aug' },
  { value: 'fall', label: 'Fall', months: 'September to December', short: 'Sep to Dec' },
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
  if (!months) return ''
  return months === 1 ? '1 month' : `${months} months`
}

/**
 * The length filter groups real lengths into the usual co-op ones, so "About 8 months" also
 * finds 6 and 9 month jobs. Same ranges as LENGTH_BUCKETS in backend/app/ingest/terms.py
 */
export const LENGTH_BUCKETS: Record<number, { label: string; range: string }> = {
  4: { label: 'About 4 months', range: '2 to 5 months' },
  8: { label: 'About 8 months', range: '6 to 9 months' },
  12: { label: 'About 12 months', range: '10 to 14 months' },
  16: { label: '16 months or more', range: '15 months or more' },
}

const MONTHS = ['Jan', 'Feb', 'Mar', 'Apr', 'May', 'Jun', 'Jul', 'Aug', 'Sep', 'Oct', 'Nov', 'Dec']
// The month each Canadian co-op term starts. Spring differs between schools so it has none
const START_MONTH: Partial<Record<Season, number>> = { winter: 0, summer: 4, fall: 8 }

/**
 * When the work term runs, worked out from its season and length.
 *   Summer 2027 and 4 months   "May to Aug 2027"
 *   Fall 2027 and 8 months     "Sep 2027 to Apr 2028"
 *   Winter 2027, no length     "Starts Jan 2027"
 *   Summer with no year        "Starts in May"
 * '' when we cannot tell, like Spring or no term at all.
 */
export function termDates(
  season: Season | null | undefined, term: string | null | undefined, months: number | null | undefined,
): string {
  const start = season ? START_MONTH[season] : undefined
  if (start === undefined) return ''
  const year = Number(/(\d{4})$/.exec(term ?? '')?.[1]) || 0
  if (!year) return `Starts in ${MONTHS[start]}`
  if (!months) return `Starts ${MONTHS[start]} ${year}`
  const endIndex = start + months - 1
  const endYear = year + Math.floor(endIndex / 12)
  const end = MONTHS[endIndex % 12]
  return endYear === year
    ? `${MONTHS[start]} to ${end} ${year}`
    : `${MONTHS[start]} ${year} to ${end} ${endYear}`
}

/** "Grad year 2027" or "Grad year 2026 or 2027". When you finish school, not the work term */
export function gradYearsLabel(years: number[]): string {
  return years.length ? `Grad year ${years.join(' or ')}` : ''
}

/** The term as people say it, or '' when the job gives none. "Open" means it did not say */
export function termLabel(term: string | null | undefined): string {
  return term && term !== 'Open' ? term : ''
}
