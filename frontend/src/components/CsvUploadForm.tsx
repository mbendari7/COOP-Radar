/**
 * Add a bunch of jobs from a CSV, like one copied out of a school co-op portal.
 * Shows how many rows got added or skipped as duplicates, plus the problems in each row.
 */

import { useRef, useState } from 'react'
import { useUploadCsv, type CsvUploadResult } from '../api/postings'

export function CsvUploadForm() {
  const fileRef = useRef<HTMLInputElement>(null)
  const [result, setResult] = useState<CsvUploadResult | null>(null)

  const mutation = useUploadCsv()

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const file = fileRef.current?.files?.[0]
    if (!file) return
    setResult(null)
    mutation.mutate(file, { onSuccess: (data) => setResult(data) })
  }

  return (
    <div className="max-w-lg">
      <h2 className="display mb-4 text-2xl text-gray-900">Upload jobs from a CSV</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="csv-file" className="label-form mb-1 block !text-gray-900">
            CSV file
          </label>
          <input
            id="csv-file"
            ref={fileRef}
            type="file"
            accept=".csv"
            required
            className="block w-full text-sm text-gray-700 file:mr-4 file:border-2 file:border-gray-900 file:bg-white file:px-4 file:py-1.5 file:text-sm file:font-bold file:text-gray-900 hover:file:bg-gray-100"
          />
          <p className="mt-1 text-xs text-gray-600">
            Required columns: title, company, city, term, deadline (YYYY-MM-DD). Max 1,000 rows.
          </p>
        </div>

        <button
          type="submit"
          disabled={mutation.isPending}
          className="btn-primary w-full"
        >
          {mutation.isPending ? 'Uploading...' : 'Upload'}
        </button>
      </form>

      {mutation.isError && (
        <div role="alert" className="mt-4 border-[1.5px] border-post-600 p-3 text-sm font-semibold text-post-700">
          {mutation.error?.message || 'Upload failed.'}
        </div>
      )}

      {result && (
        <div className="mt-4 space-y-3">
          <div className="border-[1.5px] border-air-700 bg-air-50 p-3 text-sm text-air-900">
            <strong>{result.added}</strong> added · <strong>{result.skipped_duplicates}</strong> duplicates skipped
          </div>

          {result.errors.length > 0 && (
            <div>
              <p className="text-sm font-bold text-post-700 mb-1">{result.errors.length} row error(s):</p>
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="bg-gray-100">
                    <th className="border border-gray-300 px-2 py-1 text-left">Line</th>
                    <th className="border border-gray-300 px-2 py-1 text-left">Column</th>
                    <th className="border border-gray-300 px-2 py-1 text-left">Error</th>
                  </tr>
                </thead>
                <tbody>
                  {result.errors.map((err, i) => (
                    <tr key={i}>
                      <td className="border border-gray-300 px-2 py-1">{err.row}</td>
                      <td className="border border-gray-300 px-2 py-1">{err.column}</td>
                      <td className="border border-gray-300 px-2 py-1">{err.message}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            </div>
          )}
        </div>
      )}
    </div>
  )
}
