import { useRef, useState } from 'react'
import { useMutation } from '@tanstack/react-query'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

interface RowError {
  row: number
  column: string
  message: string
}

interface CsvUploadResult {
  added: number
  skipped_duplicates: number
  errors: RowError[]
}

async function uploadCsv(file: File): Promise<CsvUploadResult> {
  const formData = new FormData()
  formData.append('file', file)
  const res = await fetch(`${API_BASE}/api/postings/upload`, {
    method: 'POST',
    credentials: 'include',
    body: formData,
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body?.detail?.message ?? `HTTP ${res.status}`)
  }
  return res.json() as Promise<CsvUploadResult>
}

export function CsvUploadForm() {
  const fileRef = useRef<HTMLInputElement>(null)
  const [result, setResult] = useState<CsvUploadResult | null>(null)

  const mutation = useMutation({
    mutationFn: uploadCsv,
    onSuccess: (data) => setResult(data),
  })

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    const file = fileRef.current?.files?.[0]
    if (!file) return
    setResult(null)
    mutation.mutate(file)
  }

  return (
    <div className="max-w-lg">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Upload Postings from CSV</h2>

      <form onSubmit={handleSubmit} className="space-y-4">
        <div>
          <label htmlFor="csv-file" className="block text-sm font-medium text-gray-700 mb-1">
            CSV file
          </label>
          <input
            id="csv-file"
            ref={fileRef}
            type="file"
            accept=".csv"
            required
            className="block w-full text-sm text-gray-700 file:mr-4 file:py-2 file:px-4 file:rounded-md file:border-0 file:text-sm file:font-medium file:bg-blue-50 file:text-blue-700 hover:file:bg-blue-100"
          />
          <p className="mt-1 text-xs text-gray-500">
            Required columns: title, company, city, term, deadline (YYYY-MM-DD). Max 1,000 rows.
          </p>
        </div>

        <button
          type="submit"
          disabled={mutation.isPending}
          className="w-full flex justify-center py-2 px-4 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
        >
          {mutation.isPending ? 'Uploading…' : 'Upload'}
        </button>
      </form>

      {mutation.isError && (
        <div role="alert" className="mt-4 p-3 rounded-md bg-red-50 text-sm text-red-700">
          {mutation.error instanceof Error ? mutation.error.message : 'Upload failed.'}
        </div>
      )}

      {result && (
        <div className="mt-4 space-y-3">
          <div className="p-3 rounded-md bg-green-50 text-sm text-green-800">
            <strong>{result.added}</strong> added · <strong>{result.skipped_duplicates}</strong> duplicates skipped
          </div>

          {result.errors.length > 0 && (
            <div>
              <p className="text-sm font-medium text-red-700 mb-1">{result.errors.length} row error(s):</p>
              <table className="w-full text-xs border-collapse">
                <thead>
                  <tr className="bg-red-50">
                    <th className="border border-red-200 px-2 py-1 text-left">Row</th>
                    <th className="border border-red-200 px-2 py-1 text-left">Column</th>
                    <th className="border border-red-200 px-2 py-1 text-left">Error</th>
                  </tr>
                </thead>
                <tbody>
                  {result.errors.map((err, i) => (
                    <tr key={i}>
                      <td className="border border-red-200 px-2 py-1">{err.row}</td>
                      <td className="border border-red-200 px-2 py-1">{err.column}</td>
                      <td className="border border-red-200 px-2 py-1">{err.message}</td>
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
