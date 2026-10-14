/**
 * Adzuna jobs must credit Adzuna, so the details panel needs to spot them by their link.
 */

import { describe, it, expect } from 'vitest'
import { isAdzuna } from '../src/utils/format'

describe('isAdzuna', () => {
  it('spots Adzuna links in Canada and the US', () => {
    expect(isAdzuna('https://www.adzuna.ca/land/ad/123?se=x')).toBe(true)
    expect(isAdzuna('https://www.adzuna.com/details/456')).toBe(true)
  })

  it('leaves employer links and bad links alone', () => {
    expect(isAdzuna('https://boards.greenhouse.io/acme/jobs/1')).toBe(false)
    expect(isAdzuna('https://notadzuna.ca/x')).toBe(false)
    expect(isAdzuna('not a url')).toBe(false)
    expect(isAdzuna(null)).toBe(false)
  })
})
