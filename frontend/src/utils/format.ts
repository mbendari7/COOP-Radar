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
