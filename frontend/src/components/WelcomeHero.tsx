/**
 * WelcomeHero — first-visit introduction on the postings page for signed-out visitors.
 * Explains what CoopRadar does in one glance and offers the demo or sign-up.
 */

import { useState } from 'react'
import AuthModal from './AuthModal'
import DemoButton from './DemoButton'

const FEATURES = [
  {
    title: 'Search every posting in one place',
    body: 'Filter by city, term, work mode, duration, and skills — or search by meaning with smart search.',
  },
  {
    title: 'Track every application',
    body: 'Save postings, move them from Applying to Offer on a board, and never miss a deadline.',
  },
  {
    title: 'Match your resume with AI',
    body: 'Upload a resume to get your best-fit postings scored and explained, then ask follow-up questions.',
  },
]

export default function WelcomeHero() {
  const [authOpen, setAuthOpen] = useState(false)

  return (
    <section
      aria-labelledby="welcome-heading"
      className="rounded-2xl bg-gradient-to-br from-blue-700 to-indigo-700 text-white p-6 sm:p-10 shadow-sm"
    >
      <h2 id="welcome-heading" className="text-2xl sm:text-3xl font-bold tracking-tight">
        Find, track, and win your next co-op.
      </h2>
      <p className="mt-2 max-w-2xl text-blue-100">
        CoopRadar brings co-op and internship postings together, keeps your applications organised,
        and tells you which roles fit your resume — and what you're missing.
      </p>

      <div className="mt-5 flex flex-wrap items-start gap-3">
        <DemoButton variant="hero" />
        <button
          type="button"
          onClick={() => setAuthOpen(true)}
          className="px-5 py-2.5 rounded-lg bg-white/10 text-white font-semibold ring-1 ring-white/40 hover:bg-white/20 focus:outline-none focus:ring-2 focus:ring-white"
        >
          Create a free account
        </button>
      </div>
      <p className="mt-2 text-xs text-blue-200">
        The demo opens a private sample account instantly — no sign-up needed.
      </p>

      <ul className="mt-8 grid gap-4 sm:grid-cols-3" role="list">
        {FEATURES.map((f) => (
          <li key={f.title} className="rounded-xl bg-white/10 p-4">
            <h3 className="font-semibold">{f.title}</h3>
            <p className="mt-1 text-sm text-blue-100">{f.body}</p>
          </li>
        ))}
      </ul>

      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} initialTab="register" />
    </section>
  )
}
