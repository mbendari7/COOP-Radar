/** Switch between plain keyword search and smart search by meaning. */

import type { SearchMode } from '../api/postings'

interface SearchModeToggleProps {
  value: SearchMode
  onChange: (mode: SearchMode) => void
}

export function SearchModeToggle({ value, onChange }: SearchModeToggleProps) {
  return (
    <div
      role="group"
      aria-label="Search mode"
      className="inline-flex overflow-hidden rounded-sm border-[1.5px] border-gray-400 bg-white"
    >
      <button
        type="button"
        aria-pressed={value === 'keyword'}
        onClick={() => onChange('keyword')}
        className={`px-3 py-1 text-sm font-semibold transition-colors focus:z-10 ${
          value === 'keyword' ? 'bg-air-700 text-white' : 'bg-white text-gray-800 hover:bg-gray-100'
        }`}
      >
        Keyword
      </button>
      <button
        type="button"
        aria-pressed={value === 'semantic'}
        onClick={() => onChange('semantic')}
        className={`border-l-[1.5px] border-gray-400 px-3 py-1 text-sm font-semibold transition-colors focus:z-10 ${
          value === 'semantic' ? 'bg-air-700 text-white' : 'bg-white text-gray-800 hover:bg-gray-100'
        }`}
      >
        Smart search
      </button>
    </div>
  )
}
