import { beforeEach, describe, expect, it } from 'vitest'
import { feedUrl } from '../src/api/postings'
import { LENGTH_BUCKETS, gradYearsLabel, lengthLabel, termDates } from '../src/components/terms'
import { previousVisit } from '../src/utils/visits'

describe('termDates', () => {
  it('shows when the work term runs from its season and length', () => {
    expect(termDates('summer', 'Summer 2027', 4)).toBe('May to Aug 2027')
    expect(termDates('winter', 'Winter 2027', 4)).toBe('Jan to Apr 2027')
    expect(termDates('fall', 'Fall 2027', 8)).toBe('Sep 2027 to Apr 2028')
    expect(termDates('summer', 'Summer 2027', 6)).toBe('May to Oct 2027')
  })

  it('gives the start when the length is unknown', () => {
    expect(termDates('winter', 'Winter 2027', null)).toBe('Starts Jan 2027')
    expect(termDates('summer', 'Summer', null)).toBe('Starts in May')
  })

  it('says nothing for spring or no term', () => {
    expect(termDates('spring', 'Spring 2027', 4)).toBe('')
    expect(termDates(null, 'Open', 4)).toBe('')
  })
})

describe('labels', () => {
  it('keeps the real length', () => {
    expect(lengthLabel(6)).toBe('6 months')
    expect(lengthLabel(null)).toBe('')
    expect(LENGTH_BUCKETS[8].range).toBe('6 to 9 months')
  })

  it('names the grad year so it is not mistaken for the term', () => {
    expect(gradYearsLabel([2027])).toBe('Grad year 2027')
    expect(gradYearsLabel([2026, 2027])).toBe('Grad year 2026 or 2027')
    expect(gradYearsLabel([])).toBe('')
  })
})

describe('feedUrl', () => {
  it('keeps the filters and drops sort and paging', () => {
    const url = feedUrl(
      { q: 'data', season: ['summer'], country: ['CA'], sort: 'deadline', order: 'asc', page: 3, page_size: 50 },
      'https://coopradar.example',
    )
    expect(url).toBe('https://coopradar.example/api/postings/feed.rss?q=data&season=summer&country=CA')
  })
})

describe('previousVisit', () => {
  beforeEach(() => {
    localStorage.clear()
    sessionStorage.clear()
  })

  it('is null the first time, then the earlier visit for the whole next session', () => {
    expect(previousVisit(new Date('2026-10-14T10:00:00Z'))).toBeNull()
    sessionStorage.clear() // a new session
    expect(previousVisit(new Date('2026-10-16T10:00:00Z'))).toBe('2026-10-14T10:00:00.000Z')
    // Same session, later page load: still counts from the earlier visit
    expect(previousVisit(new Date('2026-10-16T11:00:00Z'))).toBe('2026-10-14T10:00:00.000Z')
  })
})
