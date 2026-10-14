/**
 * Make your resume fit this job. Free, instant and with no AI (GET /api/resume/align/{id}).
 *
 * Shows plain yes or no checks, the edits to make in order, and the job's skills and words
 * split into ones the resume already has and ones worth adding if they are true.
 * It shows on a job's details when the visitor has a resume, and under each match.
 */

import { Link } from 'react-router-dom'
import { useAlignment, type ResumeAlignment } from '../api/resume'
import { CheckIcon, XIcon } from './Icons'

export default function ResumeFitPanel({ postingId, enabled = true }: { postingId: string; enabled?: boolean }) {
  const { data, isLoading, isError } = useAlignment(postingId, enabled)

  if (isLoading) {
    return <p className="text-sm text-gray-600" aria-busy="true">Comparing your resume with this job...</p>
  }
  if (isError || !data) {
    return <p className="text-sm text-gray-700">We could not compare your resume with this job right now.</p>
  }
  return <FitDetails fit={data} />
}

export function FitDetails({ fit }: { fit: ResumeAlignment }) {
  return (
    <div className="space-y-5 text-[15px]">
      {fit.checks.length > 0 && (
        <ul className="space-y-1.5" aria-label="Checks">
          {fit.checks.map((c) => (
            <li key={c.text} className="flex items-start gap-2">
              {c.ok ? (
                <CheckIcon className="mt-0.5 h-4 w-4 shrink-0 text-air-700" />
              ) : (
                <XIcon className="mt-0.5 h-4 w-4 shrink-0 text-post-600" />
              )}
              <span className="text-gray-900"><span className="sr-only">{c.ok ? 'Yes: ' : 'Not yet: '}</span>{c.text}</span>
            </li>
          ))}
        </ul>
      )}

      {fit.tips.length > 0 && (
        <div>
          <p className="label-form mb-1.5">What to change</p>
          <ol className="list-decimal space-y-1.5 pl-5 text-gray-900 marker:font-bold marker:text-gray-600">
            {fit.tips.map((t) => <li key={t}>{t}</li>)}
          </ol>
        </div>
      )}

      <div className="grid gap-4 sm:grid-cols-2">
        <WordList title="Already on your resume" items={[...fit.matched_skills, ...fit.keywords_found]} have />
        <WordList title="Worth adding, if true for you" items={[...fit.missing_skills, ...fit.keywords_missing]} have={false} />
      </div>

      <p className="text-xs text-gray-600">
        Free and read from the job's own words. Only add what you have really done. For a rewrite
        in your own voice, use Tailor my resume with <Link to="/ai-key" className="link">your AI key</Link>.
      </p>
    </div>
  )
}

function WordList({ title, items, have }: { title: string; items: string[]; have: boolean }) {
  const unique = [...new Set(items)]
  if (unique.length === 0) return null
  return (
    <div>
      <p className="label-form mb-1.5">{title}</p>
      <ul className="flex flex-wrap gap-1.5" role="list">
        {unique.map((w) => (
          <li
            key={w}
            className={`inline-flex items-center gap-1 border px-2 py-0.5 text-sm ${
              have ? 'border-air-200 bg-air-50 font-semibold text-air-900' : 'border-dashed border-gray-500 text-gray-800'
            }`}
          >
            {have && <CheckIcon className="h-3.5 w-3.5" />}
            {w}
          </li>
        ))}
      </ul>
    </div>
  )
}
