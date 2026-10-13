/** Small helpers for the postal look that more than one component needs. */

import type { PostingListItem } from '../api/postings'

/** What goes on a job's postmark. The city on top and the province or country underneath */
export function postmarkPlace(p: Pick<PostingListItem, 'city' | 'province' | 'country' | 'work_mode'>) {
  const remote = p.city === 'Remote' || (!p.city && p.work_mode === 'remote')
  const place = remote ? 'Remote' : p.city || (p.country === 'US' ? 'USA' : 'Canada')
  const region = p.country === 'US' ? (p.province ? `${p.province} USA` : 'USA') : p.province || (remote ? 'Canada' : 'CAN')
  return { place, region }
}

