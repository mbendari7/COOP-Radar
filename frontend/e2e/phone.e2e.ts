/** On a phone: nothing scrolls sideways, and a job opens on its own page. */

import { expect, test } from '@playwright/test'

test('phone layout fits the screen and opens jobs full page', async ({ page }) => {
  await page.goto('/?level=all&country=all&show_expired=true')
  await expect(page.getByRole('button', { name: 'Find jobs' })).toBeVisible()

  const overflow = await page.evaluate(() => document.documentElement.scrollWidth - window.innerWidth)
  expect(overflow).toBeLessThanOrEqual(0)

  // No side panel on phones: tapping a job goes to /postings/<id>
  await expect(page.getByRole('complementary', { name: 'Job details' })).toBeHidden()
  await page.locator('article[aria-label]').first().click()
  await expect(page).toHaveURL(/\/postings\//)
  await expect(page.getByRole('button', { name: 'Back to jobs' })).toBeVisible()
})
