/** Format an ISO date or datetime string to a short human-readable date. */
export function formatDate(value: string): string {
  const d = new Date(value)
  return d.toLocaleDateString('en-CA', { year: 'numeric', month: 'short', day: 'numeric' })
}

export function workModeLabel(mode: string): string {
  switch (mode) {
    case 'remote': return 'Remote'
    case 'hybrid': return 'Hybrid'
    case 'onsite': return 'On-site'
    default:       return mode
  }
}

/** "Toronto, ON", "Remote", or "Canada" — never a dangling comma when a part is missing. */
export function formatLocation(city: string, province: string): string {
  return [city, province].filter(Boolean).join(', ')
}

const PROVINCES: Record<string, string> = {
  AB: 'Alberta', BC: 'British Columbia', MB: 'Manitoba', NB: 'New Brunswick',
  NL: 'Newfoundland and Labrador', NS: 'Nova Scotia', NT: 'Northwest Territories',
  NU: 'Nunavut', ON: 'Ontario', PE: 'Prince Edward Island', QC: 'Quebec',
  SK: 'Saskatchewan', YT: 'Yukon',
}

/** "ON" -> "Ontario"; unknown codes are shown as they are. */
export function provinceName(code: string): string {
  return PROVINCES[code.toUpperCase()] ?? code
}

/** "today", "yesterday", "3 days ago", "2 weeks ago", else a date. */
export function timeAgo(value: string, now: Date = new Date()): string {
  const days = Math.floor((now.getTime() - new Date(value).getTime()) / 86_400_000)
  if (days <= 0) return 'today'
  if (days === 1) return 'yesterday'
  if (days < 14) return `${days} days ago`
  if (days < 60) return `${Math.floor(days / 7)} weeks ago`
  return formatDate(value)
}
