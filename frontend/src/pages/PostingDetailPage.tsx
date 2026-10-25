/**
 * One job on its own page at /postings/:id. Phones open jobs here and wide screens usually see
 * the same details in the panel next to the results. Back goes to the exact same list
 * because the list keeps everything in the URL.
 */

import { useNavigate, useParams } from 'react-router-dom'
import { usePosting } from '../api/postings'
import PostingDetailView from '../components/PostingDetailView'
import { SimilarPostings } from '../components/SimilarPostings'

export default function PostingDetailPage() {
  const { id } = useParams<{ id: string }>()
  const navigate = useNavigate()
  const { data: posting, isLoading, isError } = usePosting(id)

  const back = (
    <button
      onClick={() => navigate(-1)}
      className="link mb-5 text-sm"
    >
      Back to jobs
    </button>
  )

  if (isLoading) {
    return (
      <div className="mx-auto max-w-3xl space-y-4 px-4 py-8 animate-pulse">
        <div className="h-8 w-2/3 bg-gray-200" />
        <div className="h-4 w-1/4 bg-gray-200" />
        <div className="mt-6 space-y-2">
          {Array.from({ length: 6 }).map((_, i) => (
            <div key={i} className="h-4 bg-gray-200" style={{ width: `${60 + i * 5}%` }} />
          ))}
        </div>
      </div>
    )
  }

  if (isError || !posting) {
    return (
      <div className="mx-auto max-w-3xl px-4 py-12 text-center">
        <p className="mb-4 text-gray-700">
          {isError ? 'Something went wrong loading this job.' : 'This job was not found.'}
        </p>
        {back}
      </div>
    )
  }

  return (
    <div className="w-full px-4 py-6 sm:py-8 lg:px-6">
      {back}
      <div className="grid gap-10 lg:grid-cols-[1fr_18rem]">
        <div className="min-w-0">
          <PostingDetailView posting={posting} variant="page" />
        </div>
        <aside aria-label="Similar jobs">
          <h2 className="label-form mb-2 !text-gray-900">Similar jobs</h2>
          <SimilarPostings postingId={posting.id} />
        </aside>
      </div>
    </div>
  )
}
