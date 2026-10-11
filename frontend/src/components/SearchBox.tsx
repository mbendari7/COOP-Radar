/**
 * SearchBox — debounced keyword search input.
 * Waits 300ms after the user stops typing before calling onSearch,
 * so we don't fire an API request on every keystroke.
 */

import { useEffect, useRef, useState } from 'react'

interface Props {
  value: string
  onSearch: (value: string) => void
  placeholder?: string
}

export default function SearchBox({ value, onSearch, placeholder = 'Search postings…' }: Props) {
  const [local, setLocal] = useState(value)
  const timer = useRef<ReturnType<typeof setTimeout> | null>(null)

  // Keep local state in sync when the parent clears the value (e.g. "Clear all")
  useEffect(() => {
    setLocal(value)
  }, [value])

  function handleChange(e: React.ChangeEvent<HTMLInputElement>) {
    const next = e.target.value
    setLocal(next)

    // Cancel any pending debounce and start a fresh one
    if (timer.current) clearTimeout(timer.current)
    timer.current = setTimeout(() => {
      onSearch(next)
    }, 300)
  }

  return (
    <div className="relative">
      {/* Search icon */}
      <span className="absolute inset-y-0 left-3 flex items-center text-gray-500 pointer-events-none" aria-hidden="true">
        <svg className="h-4 w-4" fill="none" stroke="currentColor" viewBox="0 0 24 24">
          <path strokeLinecap="round" strokeLinejoin="round" strokeWidth={2}
            d="M21 21l-4.35-4.35M17 11A6 6 0 1 1 5 11a6 6 0 0 1 12 0z" />
        </svg>
      </span>
      <input
        type="search"
        role="searchbox"
        aria-label="Search postings by keyword"
        value={local}
        onChange={handleChange}
        placeholder={placeholder}
        className="
          w-full pl-9 pr-4 py-2 text-sm border border-gray-300 rounded-lg bg-white
          placeholder-gray-400 text-gray-900
          focus:outline-none focus:ring-2 focus:ring-brand-500 focus:border-transparent
        "
      />
    </div>
  )
}
