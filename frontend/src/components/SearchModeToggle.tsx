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
      className="inline-flex rounded-lg border border-gray-300 overflow-hidden bg-white"
    >
      <button
        type="button"
        aria-pressed={value === 'keyword'}
        onClick={() => onChange('keyword')}
        className={`px-3 py-1.5 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:z-10 ${
          value === 'keyword'
            ? 'bg-blue-600 text-white'
            : 'bg-white text-gray-700 hover:bg-gray-50'
        }`}
      >
        Keyword
      </button>
      <button
        type="button"
        aria-pressed={value === 'semantic'}
        onClick={() => onChange('semantic')}
        className={`px-3 py-1.5 text-sm font-medium transition-colors focus:outline-none focus:ring-2 focus:ring-blue-500 focus:z-10 border-l border-gray-300 ${
          value === 'semantic'
            ? 'bg-blue-600 text-white'
            : 'bg-white text-gray-700 hover:bg-gray-50'
        }`}
      >
        Smart search
      </button>
    </div>
  )
}
