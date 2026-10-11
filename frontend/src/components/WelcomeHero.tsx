/**
 * WelcomeHero — first-visit introduction on the jobs page for signed-out visitors.
 * One clear action ("Analyze my resume"), plus the pre-filled demo for the curious.
 */

import { Link } from 'react-router-dom'
import DemoButton from './DemoButton'

const STEPS = [
  {
    title: '1. Upload your resume',
    body: 'PDF or Word. No sign-up — you get a private account you can keep or let expire.',
  },
  {
    title: '2. See what it says',
    body: 'Skills employers can see, in-demand skills you are missing, and an AI review with tailoring tips.',
  },
  {
    title: '3. Apply to the right jobs',
    body: 'Real co-op and intern postings from Canadian employers, ranked for you — with a one-click tailoring plan for each.',
  },
]

export default function WelcomeHero() {
  return (
    <section
      aria-labelledby="welcome-heading"
      className="rounded-2xl bg-gradient-to-br from-blue-700 to-indigo-700 text-white p-6 sm:p-10 shadow-sm"
    >
      <h2 id="welcome-heading" className="text-2xl sm:text-4xl font-bold tracking-tight">
        Land your next co-op.
      </h2>
      <p className="mt-3 max-w-2xl text-blue-100 text-lg">
        Drop in your resume. CoopRadar shows what it's good at, how to tailor it, and which real
        jobs near you to apply for.
      </p>

      <div className="mt-6 flex flex-wrap items-center gap-3">
        <Link
          to="/resume"
          className="px-6 py-3 rounded-lg bg-white text-blue-800 font-semibold hover:bg-blue-50 shadow-sm focus:outline-none focus:ring-2 focus:ring-white"
        >
          Analyze my resume — free
        </Link>
        <DemoButton variant="hero-outline" label="See a demo first" />
      </div>

      <ol className="mt-8 grid gap-4 sm:grid-cols-3" role="list">
        {STEPS.map((s) => (
          <li key={s.title} className="rounded-xl bg-white/10 p-4">
            <h3 className="font-semibold">{s.title}</h3>
            <p className="mt-1 text-sm text-blue-100">{s.body}</p>
          </li>
        ))}
      </ol>
    </section>
  )
}
