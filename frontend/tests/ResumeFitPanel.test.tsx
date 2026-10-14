/**
 * Tests for Make your resume fit this job. The checks, the edits in order and the word lists.
 */

import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router-dom'
import { describe, it, expect } from 'vitest'
import { FitDetails } from '../src/components/ResumeFitPanel'
import type { ResumeAlignment } from '../src/api/resume'

const FIT: ResumeAlignment = {
  posting_id: '00000000-0000-0000-0000-000000000001',
  title: 'Financial Analyst Co-op',
  company: 'Maple Bank',
  matched_skills: ['Excel'],
  missing_skills: ['Financial Modelling'],
  keywords_found: ['budget'],
  keywords_missing: ['variance analysis'],
  checks: [
    { ok: true, text: 'Your program is one it asks for' },
    { ok: false, text: 'Your resume does not say you are free for Summer 2027' },
  ],
  tips: [
    'Add one line near the top: "Available for a 4 month Summer 2027 co-op term".',
    'Use the job\'s own words where they are true for you: variance analysis.',
  ],
}

describe('FitDetails', () => {
  it('shows each check with a yes or not yet for screen readers', () => {
    render(<MemoryRouter><FitDetails fit={FIT} /></MemoryRouter>)
    const checks = screen.getByRole('list', { name: 'Checks' })
    expect(checks).toHaveTextContent('Yes: Your program is one it asks for')
    expect(checks).toHaveTextContent('Not yet: Your resume does not say you are free for Summer 2027')
  })

  it('lists the edits in order and splits the words', () => {
    render(<MemoryRouter><FitDetails fit={FIT} /></MemoryRouter>)
    const steps = screen.getAllByRole('listitem').filter((li) => li.closest('ol'))
    expect(steps[0]).toHaveTextContent('Available for a 4 month Summer 2027 co-op term')
    expect(screen.getByText('Already on your resume').nextElementSibling).toHaveTextContent('Excel')
    expect(screen.getByText('Worth adding, if true for you').nextElementSibling).toHaveTextContent(
      'variance analysis',
    )
  })
})
