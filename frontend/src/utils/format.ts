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

/** "Toronto, ON", "Austin, TX, US", "Remote" or "Canada", never a dangling comma. */
export function formatLocation(city: string, province: string, country = 'CA'): string {
  const parts = [city, province].filter(Boolean)
  if (country === 'US' && city !== 'United States') parts.push('US')
  return parts.join(', ')
}

const PROVINCES: Record<string, string> = {
  AB: 'Alberta', BC: 'British Columbia', MB: 'Manitoba', NB: 'New Brunswick',
  NL: 'Newfoundland and Labrador', NS: 'Nova Scotia', NT: 'Northwest Territories',
  NU: 'Nunavut', ON: 'Ontario', PE: 'Prince Edward Island', QC: 'Quebec',
  SK: 'Saskatchewan', YT: 'Yukon',
}

const STATES: Record<string, string> = {
  AL: 'Alabama', AK: 'Alaska', AZ: 'Arizona', AR: 'Arkansas', CA: 'California', CO: 'Colorado',
  CT: 'Connecticut', DC: 'Washington, DC', DE: 'Delaware', FL: 'Florida', GA: 'Georgia',
  HI: 'Hawaii', ID: 'Idaho', IL: 'Illinois', IN: 'Indiana', IA: 'Iowa', KS: 'Kansas',
  KY: 'Kentucky', LA: 'Louisiana', ME: 'Maine', MD: 'Maryland', MA: 'Massachusetts',
  MI: 'Michigan', MN: 'Minnesota', MS: 'Mississippi', MO: 'Missouri', MT: 'Montana',
  NE: 'Nebraska', NV: 'Nevada', NH: 'New Hampshire', NJ: 'New Jersey', NM: 'New Mexico',
  NY: 'New York', NC: 'North Carolina', ND: 'North Dakota', OH: 'Ohio', OK: 'Oklahoma',
  OR: 'Oregon', PA: 'Pennsylvania', RI: 'Rhode Island', SC: 'South Carolina',
  SD: 'South Dakota', TN: 'Tennessee', TX: 'Texas', UT: 'Utah', VT: 'Vermont', VA: 'Virginia',
  WA: 'Washington', WV: 'West Virginia', WI: 'Wisconsin', WY: 'Wyoming',
}

/** "ON" -> "Ontario", "TX" -> "Texas"; unknown codes are shown as they are. */
export function provinceName(code: string): string {
  const c = code.toUpperCase()
  return PROVINCES[c] ?? STATES[c] ?? code
}

/** Canadian province codes vs US state codes (the two sets don't overlap). */
export function isProvince(code: string): boolean {
  return code.toUpperCase() in PROVINCES
}

export function countryName(code: string): string {
  return code === 'US' ? 'United States' : 'Canada'
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
