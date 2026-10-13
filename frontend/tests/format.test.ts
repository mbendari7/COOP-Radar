/**
 * Date helpers. A deadline like 2026-10-14 has to show as Oct 14 everywhere,
 * not as Oct 13 for people west of London.
 */

import { describe, expect, it } from 'vitest'
import { formatDate, parseDay } from '../src/utils/format'

describe('parseDay', () => {
  it('reads a plain date as that day on this computer', () => {
    const d = parseDay('2026-10-14')
    expect([d.getFullYear(), d.getMonth(), d.getDate(), d.getHours()]).toEqual([2026, 9, 14, 0])
  })

  it('still reads full datetimes the normal way', () => {
    expect(parseDay('2026-10-14T12:00:00Z').getTime()).toBe(Date.UTC(2026, 9, 14, 12))
  })
})

describe('formatDate', () => {
  it('never shows a plain date as the day before', () => {
    expect(formatDate('2026-10-14')).toContain('14')
  })
})
