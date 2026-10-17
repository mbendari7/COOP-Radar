/**
 * When this browser last opened the site, for "new since your last visit" on the jobs page.
 * Kept in this browser only. It counts from the start of the previous session, so moving
 * around the site in one session does not reset it.
 */

const LAST_VISIT = 'coopradar:lastVisit'
const VISIT_PREV = 'coopradar:visitPrev'

/** The previous visit as an ISO date and time, or null on a first visit or when storage is blocked. */
export function previousVisit(now: Date = new Date()): string | null {
  try {
    const stored = sessionStorage.getItem(VISIT_PREV)
    if (stored !== null) return stored || null
    const prev = localStorage.getItem(LAST_VISIT) ?? ''
    sessionStorage.setItem(VISIT_PREV, prev)
    localStorage.setItem(LAST_VISIT, now.toISOString())
    return prev || null
  } catch {
    return null // storage blocked, like in some private windows
  }
}
