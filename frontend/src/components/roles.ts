/** Labels for the kind of role, and the layout check shared by the job list and detail panel. */

import type { RoleType } from '../api/postings'

export const ROLE_LABELS: Record<RoleType, string> = {
  coop: 'Co-op',
  internship: 'Internship',
  new_grad: 'New grad',
  job: 'Job',
}

/** Wide enough for the list + details layout (Tailwind's lg breakpoint). */
export function splitViewVisible(): boolean {
  return typeof window !== 'undefined' && window.matchMedia?.('(min-width: 1024px)').matches === true
}

/** Field-of-study tags stored on postings (app/services/education.py FIELD_LABELS). */
export const FIELD_LABELS: Record<string, string> = {
  cs: 'Computer Science / Software',
  engineering: 'Engineering',
  electrical: 'Electrical / Electronics',
  mechanical: 'Mechanical / Mechatronics',
  data_math: 'Math, Stats or Data Science',
  business: 'Business / Commerce',
  finance: 'Finance, Accounting or Economics',
  marketing: 'Marketing / Communications',
  design: 'Design',
  it: 'IT / Information Systems',
  science: 'Science',
}
