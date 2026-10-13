/**
 * Add one job by hand. Optional fields left blank stay out of the request
 * so the backend uses its own defaults.
 */

import { useState } from 'react'
import { ApiError } from '../api/client'
import { useCreatePosting, type ManualPostingIn } from '../api/postings'

/** Leave out empty optional fields since the API turns down "" for enums and URLs. */
function cleanForm(form: ManualPostingIn): ManualPostingIn {
  return Object.fromEntries(
    Object.entries(form).filter(([, v]) => v !== '' && v !== undefined),
  ) as unknown as ManualPostingIn
}

export function ManualPostingForm() {
  const [success, setSuccess] = useState(false)
  const [form, setForm] = useState<ManualPostingIn>({
    title: '',
    company: '',
    city: '',
    term: '',
    deadline: '',
  })

  const mutation = useCreatePosting()

  function set(field: keyof ManualPostingIn) {
    return (e: React.ChangeEvent<HTMLInputElement | HTMLTextAreaElement | HTMLSelectElement>) => {
      setSuccess(false)
      setForm((prev) => ({ ...prev, [field]: e.target.value }))
    }
  }

  function handleSubmit(e: React.FormEvent) {
    e.preventDefault()
    mutation.mutate(cleanForm(form), {
      onSuccess: () => {
        setSuccess(true)
        setForm({ title: '', company: '', city: '', term: '', deadline: '' })
      },
    })
  }

  return (
    <div className="max-w-lg">
      <h2 className="display mb-4 text-2xl text-gray-900">Add a job by hand</h2>

      <form onSubmit={handleSubmit} className="space-y-4" noValidate>
        {(
          [
            { id: 'title', label: 'Title *', type: 'text', required: true, placeholder: undefined },
            { id: 'company', label: 'Company *', type: 'text', required: true, placeholder: undefined },
            { id: 'city', label: 'City *', type: 'text', required: true, placeholder: undefined },
            { id: 'term', label: 'Term *', type: 'text', required: true, placeholder: 'For example Summer 2027' },
            { id: 'deadline', label: 'Deadline *', type: 'date', required: true, placeholder: undefined },
          ] as const
        ).map(({ id, label, type, required, placeholder }) => (
          <div key={id}>
            <label htmlFor={id} className="label-form mb-1 block !text-gray-900">
              {label}
            </label>
            <input
              id={id}
              type={type}
              required={required}
              placeholder={placeholder}
              value={form[id as keyof ManualPostingIn] as string ?? ''}
              onChange={set(id as keyof ManualPostingIn)}
              className="field"
            />
          </div>
        ))}

        <div>
          <label htmlFor="work_mode" className="label-form mb-1 block !text-gray-900">
            Work mode
          </label>
          <select
            id="work_mode"
            value={form.work_mode ?? ''}
            onChange={set('work_mode')}
            className="field"
          >
            <option value="">Select</option>
            <option value="onsite">Onsite</option>
            <option value="hybrid">Hybrid</option>
            <option value="remote">Remote</option>
          </select>
        </div>

        <div>
          <label htmlFor="description" className="label-form mb-1 block !text-gray-900">
            Description
          </label>
          <textarea
            id="description"
            rows={4}
            value={form.description ?? ''}
            onChange={set('description')}
            className="field"
          />
        </div>

        <div>
          <label htmlFor="source_url" className="label-form mb-1 block !text-gray-900">
            Source URL
          </label>
          <input
            id="source_url"
            type="url"
            value={form.source_url ?? ''}
            onChange={set('source_url')}
            className="field"
            placeholder="https://"
          />
        </div>

        <button
          type="submit"
          disabled={mutation.isPending}
          className="btn-primary w-full"
        >
          {mutation.isPending ? 'Saving...' : 'Add posting'}
        </button>
      </form>

      {success && (
        <div role="status" className="mt-4 border-[1.5px] border-air-700 bg-air-50 p-3 text-sm font-semibold text-air-800">
          Job added.
        </div>
      )}

      {mutation.isError && (
        <div role="alert" className="mt-4 border-[1.5px] border-post-600 p-3 text-sm font-semibold text-post-700">
          {mutation.error instanceof ApiError && mutation.error.code === 'DUPLICATE'
            ? 'A job like this is already there.'
            : mutation.error instanceof ApiError && mutation.error.code === 'VALIDATION_ERROR'
              ? 'Please fill in title, company, city, term and deadline.'
              : 'The job was not added. Please try again.'}
        </div>
      )}
    </div>
  )
}
