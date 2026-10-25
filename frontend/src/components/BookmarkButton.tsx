/**
 * Save or unsave a job.
 *
 * A filled bookmark means it is saved and an outline means it is not.
 * If nobody is signed in, clicking goes to the sign in page and comes back after.
 * It flips right away and then lets the server confirm.
 */

import { useState } from 'react'
import { useLocation, useNavigate } from 'react-router-dom'
import { useMe } from '../api/auth'
import { useSavePosting, useUnsavePosting } from '../api/saved'

interface Props {
  postingId: string
  savedId?: string       // there when the job is already saved
  isSaved: boolean
  onSaved?: (savedId: string) => void
  onUnsaved?: () => void
}

export default function BookmarkButton({ postingId, savedId, isSaved, onSaved, onUnsaved }: Props) {
  const { data: me } = useMe()
  const navigate = useNavigate()
  const location = useLocation()
  const [optimistic, setOptimistic] = useState<boolean | null>(null)

  const savePosting = useSavePosting()
  const unsavePosting = useUnsavePosting()

  const effectivelySaved = optimistic !== null ? optimistic : isSaved
  const isPending = savePosting.isPending || unsavePosting.isPending

  const handleClick = async (e: React.MouseEvent) => {
    e.stopPropagation()  // do not open the job when clicking the bookmark

    if (!me) {
      navigate(`/sign-in?next=${encodeURIComponent(location.pathname + location.search)}`)
      return
    }

    if (effectivelySaved && savedId) {
      setOptimistic(false)
      try {
        await unsavePosting.mutateAsync(savedId)
        onUnsaved?.()
      } catch {
        setOptimistic(true)  // put it back if it failed
      }
    } else {
      setOptimistic(true)
      try {
        const result = await savePosting.mutateAsync(postingId)
        onSaved?.(result.id)
      } catch {
        setOptimistic(false)  // put it back if it failed
      }
    }
    setOptimistic(null)  // now the server's answer takes over
  }

  return (
      <button
        onClick={handleClick}
        disabled={isPending}
        aria-label={effectivelySaved ? 'Remove from saved postings' : 'Save posting'}
        className={`
          rounded-sm p-1.5 transition-colors
          ${effectivelySaved ? 'text-post-600 hover:text-post-800' : 'text-gray-600 hover:text-post-600'}
          ${isPending ? 'opacity-50 cursor-wait' : ''}
        `}
      >
        {effectivelySaved ? (
          // Filled bookmark
          <svg xmlns="http://www.w3.org/2000/svg" viewBox="0 0 24 24" fill="currentColor" className="w-5 h-5" aria-hidden="true">
            <path fillRule="evenodd" d="M6.32 2.577a49.255 49.255 0 0111.36 0c1.497.174 2.57 1.46 2.57 2.93V21a.75.75 0 01-1.085.67L12 18.089l-7.165 3.583A.75.75 0 013.75 21V5.507c0-1.47 1.073-2.756 2.57-2.93z" clipRule="evenodd" />
          </svg>
        ) : (
          // Outline bookmark
          <svg xmlns="http://www.w3.org/2000/svg" fill="none" viewBox="0 0 24 24" strokeWidth={1.5} stroke="currentColor" className="w-5 h-5" aria-hidden="true">
            <path strokeLinecap="round" strokeLinejoin="round" d="M17.593 3.322c1.1.128 1.907 1.077 1.907 2.185V21L12 17.25 4.5 21V5.507c0-1.108.806-2.057 1.907-2.185a48.507 48.507 0 0111.186 0z" />
          </svg>
        )}
      </button>
  )
}
