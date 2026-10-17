/**
 * Keeping up with new jobs, on the jobs page.
 *
 * NewSinceLastVisit  a bar that says how many jobs for this search came in since the last visit,
 *                    with a button to show only those (utils/visits.ts keeps the last visit).
 * GetUpdates         a button that opens the RSS feed link for this exact search. A feed reader
 *                    or a feed to email service then brings new jobs to the student on its own.
 */

import { useEffect, useRef, useState } from 'react'
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
  const [open, setOpen] = useState(false)
  const [copied, setCopied] = useState(false)
  const box = useRef<HTMLDivElement>(null)
  const url = feedUrl(params)

  useEffect(() => {
    if (!open) return
    const close = (e: MouseEvent | KeyboardEvent) => {
      if (e instanceof KeyboardEvent ? e.key === 'Escape' : !box.current?.contains(e.target as Node)) setOpen(false)
    }
    document.addEventListener('mousedown', close)
    document.addEventListener('keydown', close)
    return () => {
      document.removeEventListener('mousedown', close)
      document.removeEventListener('keydown', close)
    }
  }, [open])

  async function copy() {
    try {
      await navigator.clipboard.writeText(url)
      setCopied(true)
      setTimeout(() => setCopied(false), 2000)
    } catch {
      setCopied(false)
    }
  }

  return (
    <div className="relative" ref={box}>
      <button
        type="button"
        className="btn-secondary px-3 py-1.5 text-sm"
        aria-expanded={open}
        aria-controls="job-updates-panel"
        onClick={() => setOpen((o) => !o)}
      >
        Get updates
      </button>
      {open && (
        <div
          id="job-updates-panel"
          className="absolute right-0 z-30 mt-2 w-[min(22rem,calc(100vw-2rem))] border border-gray-300 bg-white p-4 text-sm shadow-lg"
        >
          <p className="font-bold text-gray-900">Get new jobs for this search</p>
          <p className="mt-1 text-gray-700">
            We check every employer every 6 hours. Copy this link into a feed reader like Feedly or
            Inoreader, or a feed to email service like Blogtrottr, and new jobs for these exact
            filters come to you.
          </p>
          <label htmlFor="feed-url" className="label-form mt-3 block">Feed link</label>
          <div className="mt-1 flex gap-2">
            <input id="feed-url" readOnly value={url} className="field min-w-0 flex-1 py-1.5 text-xs" onFocus={(e) => e.target.select()} />
            <button type="button" className="btn-primary px-3 py-1.5 text-sm" onClick={copy}>
              {copied ? 'Copied' : 'Copy'}
            </button>
          </div>
          <a href={url} target="_blank" rel="noopener noreferrer" className="link mt-2 inline-block text-xs">
            Open the feed
          </a>
        </div>
      )}
    </div>
  )
}
