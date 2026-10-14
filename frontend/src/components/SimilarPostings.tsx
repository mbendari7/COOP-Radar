/** Jobs that read most like this one. Only there when smart search is on. */

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
          <div key={i} className="h-16 animate-pulse bg-gray-100" />
        ))}
      </div>
    )
  }

  if (isError || !data) {
    return null
  }

  if (data.items.length === 0) {
    return (
      <p className="text-sm text-gray-600">Similar jobs show up here when smart search is on.</p>
    )
  }

  return (
    <ul className="divide-y divide-gray-200 border-t border-gray-300" aria-label="Similar postings">
      {data.items.map((item) => (
        <li key={item.id} className="py-3">
          <Link to={`/postings/${item.id}`} className="group block">
            <p className="line-clamp-2 text-sm font-bold text-gray-900 group-hover:text-air-700">{item.title}</p>
            <p className="mt-0.5 text-xs text-gray-700">{item.company} · {item.city}</p>
            <p className="label-form mt-1 !text-air-700">
              {Math.round(item.similarity * 100)}% similar
            </p>
          </Link>
        </li>
      ))}
    </ul>
  )
}
