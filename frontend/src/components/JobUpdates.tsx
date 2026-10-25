/**
 * Keeping up with new jobs, on the jobs page.
 *
 * NewSinceLastVisit  a bar that says how many jobs for this search came in since the last visit,
 *                    with a button to show only those (utils/visits.ts keeps the last visit).
 * GetUpdates         a fold out with the RSS feed link for this exact search. A feed reader
 *                    or a feed to email service then brings new jobs to the student on its own.
 */

import { useState } from 'react'
import { feedUrl, usePostings, type PostingListParams } from '../api/postings'
import { previousVisit } from '../utils/visits'

export function NewSinceLastVisit({
  params, onShow, active,
}: {
  params: PostingListParams
  onShow: (since: string) => void
  /** True when the list already shows only the new jobs */
  active: boolean
}) {
  const [since] = useState(previousVisit)
  const { data } = usePostings(
    { ...params, added_since: since ?? undefined, page: 1, page_size: 10 },
    { enabled: Boolean(since) && !active },
  )
  if (!since || active || !data || data.total === 0) return null
  const day = new Date(since).toLocaleDateString(undefined, { month: 'short', day: 'numeric' })
  return (
    <div className="flex flex-wrap items-center justify-between gap-2 border border-air-200 bg-air-50 px-3 py-2 text-sm" role="status">
      <span>
        <span className="font-bold text-gray-900">{data.total.toLocaleString()} new {data.total === 1 ? 'job' : 'jobs'}</span>{' '}
        for this search since your last visit on {day}.
      </span>
      <button type="button" className="link font-semibold" onClick={() => onShow(since)}>
        Show only the new ones
      </button>
    </div>
  )
}

export function GetUpdates({ params }: { params: PostingListParams }) {
  const [copied, setCopied] = useState(false)
  const url = feedUrl(params)

  async function copy() {
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  // Opens in place under its heading, never over the page
  return (
    <details className="group text-sm">
      <summary className="flex cursor-pointer list-none items-center justify-between text-[13px] font-semibold text-gray-900 [&::-webkit-details-marker]:hidden">
        Get new jobs for this search
        <span className="text-gray-500 transition-transform group-open:rotate-90" aria-hidden="true">›</span>
      </summary>
      <p className="mt-2 text-[13px] text-gray-700">
        We check every employer every 6 hours. Paste this link into a feed reader like Feedly, or a
        feed to email service like Blogtrottr, and new jobs for these filters come to you.
      </p>
      <label htmlFor="feed-url" className="sr-only">Feed link</label>
      <div className="mt-2 flex gap-2">
        <input id="feed-url" readOnly value={url} className="field min-w-0 flex-1 py-1.5 text-xs" onFocus={(e) => e.target.select()} />
        <button type="button" className="btn-secondary px-3 py-1.5 text-sm" onClick={copy}>
          {copied ? 'Copied' : 'Copy'}
        </button>
      </div>
    </details>
  )
}
