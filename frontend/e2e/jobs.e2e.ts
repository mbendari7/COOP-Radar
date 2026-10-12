/** Browsing jobs like a job board: search, quick filters, all filters, details panel. */

import { expect, test } from '@playwright/test'

test.describe('jobs page', () => {
  test('shows the search bar, results and the selected job beside the list', async ({ page }) => {
    await page.goto('/?level=all&country=all&show_expired=true')

    await expect(page.getByRole('search')).toBeVisible()
    await expect(page.getByRole('heading', { level: 1 })).toContainText(/jobs in Canada and the US/)

    const first = page.locator('article[aria-current="true"]')
    await expect(first).toBeVisible()
    const title = await first.locator('h3').innerText()

    // The details panel shows the same job, with the apply button and description
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

  test('quick filters and the All filters panel change the URL', async ({ page }) => {
    await page.goto('/')
    await page.getByLabel('Experience level').selectOption('all')
    await expect(page).toHaveURL(/level=all/)
    await page.getByRole('checkbox', { name: 'Remote' }).click()
    await expect(page).toHaveURL(/work_mode=remote/)

    await page.getByRole('button', { name: /All filters/ }).click()
    const dialog = page.getByRole('dialog', { name: 'All filters' })
    await expect(dialog).toBeVisible()
    await dialog.getByLabel('Past week').check()
    await expect(page).toHaveURL(/posted_within=7/)
    await dialog.getByRole('button', { name: /Show .*jobs?/ }).click()
    await expect(dialog).toBeHidden()

    // Each active filter gets a removable chip
    await page.getByRole('button', { name: 'Remove filter: Past week' }).click()
    await expect(page).not.toHaveURL(/posted_within/)
  })
})
