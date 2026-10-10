import { Link } from 'react-router-dom'
import { useSimilarPostings } from '../api/postings'

interface SimilarPostingsProps {
  postingId: string
}

export function SimilarPostings({ postingId }: SimilarPostingsProps) {
  const { data, isLoading, isError } = useSimilarPostings(postingId)

  if (isLoading) {
    return (
      <div className="space-y-3" aria-busy="true" aria-label="Loading similar postings">
        {[...Array(3)].map((_, i) => (
          <div key={i} className="animate-pulse rounded-md bg-gray-100 h-16" />
        ))}
      </div>
    )
  }

  if (isError || !data) {
    return null
  }

  if (data.items.length === 0) {
    return (
      <p className="text-sm text-gray-500">No similar postings found.</p>
    )
  }

  return (
    <ul className="space-y-3" aria-label="Similar postings">
      {data.items.map((item) => (
        <li key={item.id} className="rounded-md border border-gray-200 p-3 hover:bg-gray-50 transition-colors">
          <Link to={`/postings/${item.id}`} className="block">
            <p className="text-sm font-medium text-gray-900 line-clamp-2">{item.title}</p>
            <p className="text-xs text-gray-500 mt-0.5">{item.company} · {item.city}</p>
            <p className="text-xs text-blue-600 mt-1">
              {Math.round(item.similarity * 100)}% match
            </p>
          </Link>
        </li>
      ))}
    </ul>
  )
}
