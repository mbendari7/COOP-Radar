import { useState } from 'react'
import { useMutation, useQueryClient } from '@tanstack/react-query'

const API_BASE = import.meta.env.VITE_API_URL ?? ''

interface ManualPostingIn {
  title: string
  company: string
  city: string
  term: string
  deadline: string
  province?: string
  work_mode?: 'onsite' | 'hybrid' | 'remote'
  duration_months?: number
  description?: string
  skills?: string[]
  source_url?: string
}

async function createPosting(data: ManualPostingIn) {
  const res = await fetch(`${API_BASE}/api/postings`, {
    method: 'POST',
    credentials: 'include',
    headers: { 'Content-Type': 'application/json' },
    body: JSON.stringify({
      ...data,
      skills: data.skills ?? [],
    }),
  })
  if (!res.ok) {
    const body = await res.json().catch(() => ({}))
    throw new Error(body?.detail?.code ?? `HTTP ${res.status}`)
  }
  return res.json()
}

export function ManualPostingForm() {
  const qc = useQueryClient()
  const [success, setSuccess] = useState(false)
  const [form, setForm] = useState<ManualPostingIn>({
    title: '',
    company: '',
    city: '',
    term: '',
    deadline: '',
  })

  const mutation = useMutation({
    mutationFn: createPosting,
    onSuccess: () => {
      setSuccess(true)
      setForm({ title: '', company: '', city: '', term: '', deadline: '' })
      void qc.invalidateQueries({ queryKey: ['postings'] })
    },
  })

  function set(field: keyof ManualPostingIn) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      setSuccess(false)
      setForm((prev) => ({ ...prev, [field]: e.target.value }))
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    mutation.mutate({
      ...form,
      skills: form.skills,
    })
  }

  return (
    <div className="max-w-lg">
      <h2 className="text-lg font-semibold text-gray-900 mb-4">Add a Posting Manually</h2>

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {(
          [
            { id: 'title', label: 'Title *', type: 'text', required: true },
            { id: 'company', label: 'Company *', type: 'text', required: true },
            { id: 'city', label: 'City *', type: 'text', required: true },
            { id: 'term', label: 'Term *', type: 'text', required: true, placeholder: 'e.g. Summer 2027' },
            { id: 'deadline', label: 'Deadline *', type: 'date', required: true },
          ] as const
        ).map(({ id, label, type, required, placeholder }) => (
          <div key={id}>
            <label htmlFor={id} className="block text-sm font-medium text-gray-700 mb-1">
              {label}
            </label>
            <input
              id={id}
              type={type}
              required={required}
              placeholder={placeholder}
              value={form[id as keyof ManualPostingIn] as string ?? ''}
              onChange={set(id as keyof ManualPostingIn)}
              className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
        ))}

        <div>
          <label htmlFor="work_mode" className="block text-sm font-medium text-gray-700 mb-1">
            Work mode
          </label>
          <select
            id="work_mode"
            value={form.work_mode ?? ''}
            onChange={set('work_mode')}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          >
            <option value="">— Select —</option>
            <option value="onsite">Onsite</option>
            <option value="hybrid">Hybrid</option>
            <option value="remote">Remote</option>
          </select>
        </div>

        <div>
          <label htmlFor="description" className="block text-sm font-medium text-gray-700 mb-1">
            Description
          </label>
          <textarea
            id="description"
            rows={4}
            value={form.description ?? ''}
            onChange={set('description')}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
        </div>

        <div>
          <label htmlFor="source_url" className="block text-sm font-medium text-gray-700 mb-1">
            Source URL
          </label>
          <input
            id="source_url"
            type="url"
            value={form.source_url ?? ''}
            onChange={set('source_url')}
            className="w-full rounded-md border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            placeholder="https://…"
          />
        </div>

        <button
          type="submit"
          disabled={mutation.isPending}
          className="w-full flex justify-center py-2 px-4 rounded-md bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
        >
          {mutation.isPending ? 'Saving…' : 'Add posting'}
        </button>
      </form>

      {success && (
        <div role="status" className="mt-4 p-3 rounded-md bg-green-50 text-sm text-green-800">
          Posting added successfully.
        </div>
      )}

      {mutation.isError && (
        <div role="alert" className="mt-4 p-3 rounded-md bg-red-50 text-sm text-red-700">
          {mutation.error instanceof Error && mutation.error.message === 'DUPLICATE'
            ? 'A similar posting already exists.'
            : 'Failed to add posting. Please try again.'}
        </div>
      )}
    </div>
  )
}
