/**
 * SearchBox: debounced keyword search input.
 * Waits 300ms after the user stops typing before calling onSearch,
 * so we don't fire an API request on every keystroke.
 */

import { useEffect, useRef, useState } from 'react'
import { SearchIcon } from './Icons'

interface Props {
  value: string
  onSearch: (value: string) => void
  placeholder?: string
}

export default function SearchBox({ value, onSearch, placeholder = 'Search job title, company or skill' }: Props) {
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
      <span className="absolute inset-y-0 left-3.5 flex items-center text-gray-500 pointer-events-none" aria-hidden="true">
        <SearchIcon className="h-5 w-5" />
      </span>
      <input
        type="search"
        role="searchbox"
        aria-label="Search postings by keyword"
        value={local}
        onChange={handleChange}
        placeholder={placeholder}
        className="
          w-full pl-11 pr-4 py-2.5 text-base border border-gray-300 rounded-lg bg-white
          placeholder-gray-500 text-gray-900
          focus:outline-none focus:ring-2 focus:ring-blue-600 focus:border-transparent
        "
      />
    </div>
  )
}
