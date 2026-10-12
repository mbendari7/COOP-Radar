/**
 * WelcomeHero: the introduction at the top of the jobs page for visitors who haven't
 * matched a resume yet. One main action (match my resume) and a plain "how it works".
 */

import { Link } from 'react-router-dom'
import DemoButton from './DemoButton'
import { ArrowRightIcon, BriefcaseIcon, FileIcon, PenIcon } from './Icons'

const STEPS = [
  {
    icon: BriefcaseIcon,
    title: 'Pick what you want',
    body: 'Software, data, design, business and more. Choose a province or remote.',
  },
  {
    icon: FileIcon,
    title: 'Upload your resume',
    body: 'PDF or Word. No sign-up. We read your skills and rank real openings for you.',
  },
  {
    icon: PenIcon,
    title: 'Apply with a better resume',
    body: 'See which skills each job wants that you are missing, and get tailoring tips.',
  },
]

export default function WelcomeHero({ jobs, employers }: { jobs?: number; employers?: number }) {
  return (
    <section
      aria-labelledby="welcome-heading"
      className="rounded-xl border border-gray-200 bg-white p-6 sm:p-8 lg:p-10"
    >
      <div className="grid gap-8 lg:grid-cols-[1.1fr_1fr] lg:gap-12">
        <div>
          <p className="text-sm font-medium text-blue-700">For students in Canada</p>
          <h2 id="welcome-heading" className="mt-2 text-3xl font-bold tracking-tight text-gray-900 sm:text-4xl">
            Find co-op and intern jobs that fit your resume.
          </h2>
          <p className="mt-3 max-w-xl text-lg text-gray-600">
            Tell us what kind of job you want, upload your resume, and see the openings you have the
            best shot at, with the skills each one is looking for.
          </p>

          <div className="mt-6 flex flex-wrap items-center gap-3">
            <Link
              to="/resume"
              className="inline-flex items-center gap-2 rounded-lg bg-blue-700 px-5 py-3 font-semibold text-white hover:bg-blue-800 focus:outline-none focus:ring-2 focus:ring-blue-600 focus:ring-offset-2"
            >
              Match my resume
              <ArrowRightIcon className="h-4 w-4" />
            </Link>
            <DemoButton variant="hero-outline" label="Try it with a sample resume" />
          </div>

          {jobs !== undefined && jobs > 0 && (
            <p className="mt-5 text-sm text-gray-500">
              <span className="font-semibold text-gray-800">{jobs.toLocaleString()}</span> open jobs
              {employers ? (
                <> from <span className="font-semibold text-gray-800">{employers}</span> employers</>
              ) : null}
              , taken from their own career pages and refreshed every few hours.
            </p>
          )}
        </div>

        <ol className="space-y-5 lg:border-l lg:border-gray-100 lg:pl-10" role="list">
          {STEPS.map((s, i) => (
            <li key={s.title} className="flex gap-4">
              <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-lg bg-blue-50 text-blue-700">
                <s.icon className="h-5 w-5" />
              </span>
              <div>
                <h3 className="font-semibold text-gray-900">
                  <span className="text-gray-400">{i + 1}.</span> {s.title}
                </h3>
                <p className="mt-0.5 text-sm text-gray-600">{s.body}</p>
              </div>
            </li>
          ))}
        </ol>
      </div>
    </section>
  )
}
