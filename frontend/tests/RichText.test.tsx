/**
 * RichText tests — the AI's headings, bullets, and bold text render as plain elements.
 */

import { render, screen } from '@testing-library/react'
import { describe, expect, it } from 'vitest'
import RichText from '../src/components/RichText'

describe('RichText', () => {
  it('renders headings, bullets, bold, and citations without HTML injection', () => {
    const { container } = render(
      <RichText text={'## Fit\nGood **match**.\n- Lead with your API project\n- Resume: built REST APIs\n<b>raw</b>'} />,
    )
    expect(screen.getByText('Fit').closest('p')).toHaveClass('font-semibold')
    expect(screen.getByText('match').tagName).toBe('STRONG')
    expect(container.querySelectorAll('li')).toHaveLength(2)
    expect(screen.getByText('Resume:', { exact: false }).tagName).toBe('STRONG')
    // Raw HTML stays text
    expect(screen.getByText('<b>raw</b>')).toBeInTheDocument()
  })
})
