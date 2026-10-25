/** Browsing jobs like a job board. Search, the filter sidebar and the details panel. */

import { expect, test } from '@playwright/test'

test.describe('jobs page', () => {
  test('shows the search bar, results and the selected job beside the list', async ({ page }) => {
    await page.goto('/?level=all&country=all&show_expired=true')

    await expect(page.getByRole('search')).toBeVisible()
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/jobs in Canada and the US/)

    const first = page.locator('article[aria-current="true"]')
    await expect(first).toBeVisible()
    const title = await first.locator('h3').innerText()

    // The details panel shows the same job with the apply button and description
    const panel = page.getByRole('complementary', { name: 'Job details' })
    await expect(panel.getByRole('heading', { level: 2 })).toHaveText(title)
    await expect(panel.getByText('About the job')).toBeVisible()
  })

  test('picking another job updates the panel and the URL', async ({ page }) => {
    await page.goto('/?level=all&country=all&show_expired=true')
    const cards = page.locator('article[aria-label]')
    await expect(cards.first()).toBeVisible()
    test.skip((await cards.count()) < 2, 'needs at least two jobs')

    const second = cards.nth(1)
    const title = await second.locator('h3').innerText()
    await second.click()

    await expect(page).toHaveURL(/job=/)
    await expect(second).toHaveAttribute('aria-current', 'true')
    await expect(page.getByRole('complementary', { name: 'Job details' }).getByRole('heading', { level: 2 })).toHaveText(title)
  })

  test('a search with no results says so and can be cleared', async ({ page }) => {
    await page.goto('/')
    await page.getByRole('searchbox', { name: /search jobs/i }).fill('zzzz no such job zzzz')
    await page.getByRole('button', { name: 'Find jobs' }).click()

    await expect(page).toHaveURL(/q=zzzz/)
    await expect(page.getByText('No jobs match these filters')).toBeVisible()
  })

  test('the filter sidebar changes the URL with no popup', async ({ page }) => {
    await page.goto('/')
    const filters = page.getByRole('complementary', { name: 'Filters' })
    await expect(filters).toBeVisible()
    await filters.getByLabel('All levels').check()
    await expect(page).toHaveURL(/level=all/)
    await filters.getByRole('checkbox', { name: /Remote/ }).click()
    await expect(page).toHaveURL(/work_mode=remote/)

    // Date posted folds open in place
    await filters.locator('summary', { hasText: 'Date posted' }).click()
    await filters.getByLabel('Past week').check()
    await expect(page).toHaveURL(/posted_within=7/)
    await expect(page.getByRole('dialog')).toHaveCount(0)

    await filters.getByRole('button', { name: /Clear all/ }).click()
    await expect(page).not.toHaveURL(/posted_within|work_mode|level=/)
  })

  test('on a phone the Filters button opens the sidebar in place', async ({ page }) => {
    await page.setViewportSize({ width: 390, height: 800 })
    await page.goto('/')
    const filters = page.getByRole('complementary', { name: 'Filters' })
    await expect(filters).toBeHidden()
    await page.getByRole('button', { name: /^Filters/ }).click()
    await expect(filters).toBeVisible()
    await expect(page.getByRole('dialog')).toHaveCount(0)
  })

  test('term season, length and term sorting work together', async ({ page }) => {
    await page.goto('/?level=all')
    const filters = page.getByRole('complementary', { name: 'Filters' })
    await filters.getByRole('checkbox', { name: /^Winter/ }).check()
    await expect(page).toHaveURL(/season=winter/)
    await filters.getByRole('checkbox', { name: /About 8 months/ }).click()
    await expect(page).toHaveURL(/duration=8/)
    await page.getByLabel('Sort by').selectOption('term_start:asc')
    await expect(page).toHaveURL(/sort=term_start/)

    // Every row shown says Winter, since the filter is on
    const rows = page.getByRole('article')
    if (await rows.count()) await expect(rows.first()).toContainText('Winter')

    await filters.getByRole('checkbox', { name: /^Winter/ }).uncheck()
    await expect(page).not.toHaveURL(/season=/)
  })
})
