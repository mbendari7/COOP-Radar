/** The main flow: upload a resume without an account and get matches that know your studies. */

import { expect, test } from '@playwright/test'
import { resumePdf } from './pdf'

const RESUME = [
  'Jordan Student',
  'EDUCATION',
  'University of Waterloo',
  'Bachelor of Science, Computer Science (Co-op)',
  'Expected graduation: April 2028',
  'SKILLS',
  'Python, SQL, React, TypeScript, Git',
]

test('upload a resume with no account and see why each job fits', async ({ page }) => {
  await page.goto('/resume')
  await expect(page.getByRole('heading', { name: 'Find co-op jobs that fit you' })).toBeVisible()

  // A segmented control: the radio is hidden inside its label
  await page.getByText('Co-op, internship or entry-level', { exact: true }).click()
  await page.getByLabel('United States').check()
  await page.locator('#resume-file').setInputFiles({
    name: 'resume.pdf', mimeType: 'application/pdf', buffer: resumePdf(RESUME),
  })

  // A temporary account was created and the resume read
  await expect(page.getByRole('tab', { name: /Jobs that fit your resume/ })).toBeVisible({ timeout: 30_000 })
  await expect(page.getByText(/We read your resume: Computer Science, Bachelor's, graduating 2028/)).toBeVisible()
  await expect(page.getByText(/temporary account/i).first()).toBeVisible()

  // Matches (if any fit) explain themselves
  const matches = page.getByRole('list', { name: 'Matched jobs' })
  if (await matches.isVisible()) {
    await expect(matches.getByText('Why it fits').first()).toBeVisible()
  } else {
    await expect(page.getByText('No open jobs fit yet')).toBeVisible()
  }

  // Free resume feedback works without an AI key
  await page.getByRole('tab', { name: 'Resume feedback' }).click()
  await expect(page.getByText('Skills employers can see')).toBeVisible()
})

test('rejects a file that is not a resume before uploading', async ({ page }) => {
  await page.goto('/resume')
  await page.locator('#resume-file').setInputFiles({
    name: 'photo.png', mimeType: 'image/png', buffer: Buffer.from('not a resume'),
  })
  await expect(page.getByRole('alert')).toContainText('PDF or Word')
})
