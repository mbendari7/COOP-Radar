/**
 * End-to-end tests: a real browser clicking through the running site.
 *
 * Start the site first (`python start.py`, or `--hosted` as CI does), then:
 *   npm run test:e2e                          (against http://localhost:8000)
 *   E2E_BASE_URL=http://localhost:8080 npm run test:e2e
 * Tests are written to pass with any data: sample postings in CI or real imported jobs.
 */

import { defineConfig, devices } from '@playwright/test'

export default defineConfig({
  testDir: './e2e',
  // *.e2e.ts, so Vitest (which runs *.test / *.spec files) never picks these up
  testMatch: '**/*.e2e.ts',
  timeout: 60_000,
  // Matching runs over every open job, so give results a moment under parallel load
  expect: { timeout: 10_000 },
  retries: process.env.CI ? 1 : 0,
  reporter: process.env.CI ? 'github' : 'list',
  use: {
    baseURL: process.env.E2E_BASE_URL ?? 'http://localhost:8000',
    // Locally you can reuse an installed browser: E2E_CHANNEL=msedge or chrome
    channel: process.env.E2E_CHANNEL || undefined,
    trace: 'retain-on-failure',
  },
  projects: [
    {
      name: 'desktop',
      use: { ...devices['Desktop Chrome'], viewport: { width: 1366, height: 900 } },
      testIgnore: '**/phone.e2e.ts',
    },
    { name: 'phone', use: { ...devices['Pixel 7'] }, testMatch: '**/phone.e2e.ts' },
  ],
})
