/**
 * The app shell. Router, the red top bar, the footer and the routes.
 *
 * Main tabs for everyone are Find jobs, Match my resume, Tracker and AI key.
 * On the right, signed in people get Account and Sign out, everyone else gets Try the demo and Sign in.
 * Temporary guest or demo accounts get a strip under the bar offering to keep the account.
 */

import { lazy, Suspense } from 'react'
import { Link, NavLink, Navigate, Route, Routes, useLocation } from 'react-router-dom'
import { useAiKey } from './api/aiKey'
import { useMe, useLogout } from './api/auth'
import DemoBanner from './components/DemoBanner'
import DemoButton from './components/DemoButton'
import { LogoMark } from './components/Icons'
import PostingDetailPage from './pages/PostingDetailPage'
import PostingsListPage from './pages/PostingsListPage'

// Load the heavier pages only when someone opens them so the first load stays small
const ResumePage = lazy(() => import('./pages/ResumePage'))
const AiKeyPage = lazy(() => import('./pages/AiKeyPage'))
const SavedPostingsPage = lazy(() => import('./pages/SavedPostingsPage'))
const AccountSettingsPage = lazy(() => import('./pages/AccountSettingsPage'))
const SignInPage = lazy(() => import('./pages/SignInPage'))
const AdminSourcesPage = lazy(() =>
  import('./pages/AdminSourcesPage').then((m) => ({ default: m.AdminSourcesPage }))
)
const CsvUploadPage = lazy(() =>
  import('./components/CsvUploadForm').then((m) => ({ default: m.CsvUploadForm }))
)
const ManualPostingPage = lazy(() =>
  import('./components/ManualPostingForm').then((m) => ({ default: m.ManualPostingForm }))
)

/** CSV import and the one job form on the same page. */
function AddPostingsPage() {
  return (
    <div className="mx-auto max-w-2xl space-y-12 p-6">
      <CsvUploadPage />
      <ManualPostingPage />
    </div>
  )
}

/** Tabs on the red bar. The open one gets a white bar under it. */
function navClass({ isActive }: { isActive: boolean }): string {
  return `relative flex shrink-0 items-center px-3 text-[15px] font-semibold transition-colors after:absolute after:inset-x-3 after:bottom-0 after:h-[3px] ${
    isActive ? 'text-white after:bg-white' : 'text-post-50 hover:text-white after:bg-transparent hover:after:bg-white/40'
  }`
}

function Header() {
  const { data: me, isLoading } = useMe()
  const aiKey = useAiKey()
  const logout = useLogout()
  const location = useLocation()
  // Come back to the same page after signing in
  const next = location.pathname === '/sign-in' ? '/' : `${location.pathname}${location.search}`

  return (
    <header className="sticky top-0 z-30">
      <div className="bg-post-600 text-white">
        {/* One row on wide screens. On phones the tabs drop to a second row so nothing hides off screen */}
        <div className="flex w-full flex-wrap items-center px-4 lg:px-6">
          <Link to="/" className="order-1 flex h-14 shrink-0 items-center gap-2.5" aria-label="CoopRadar home">
            <LogoMark className="h-7 w-7 text-white sm:h-8 sm:w-8" />
            <span className="stretch-condensed text-[19px] font-extrabold uppercase tracking-[0.03em] sm:text-[22px]">CoopRadar</span>
          </Link>

          <nav
            className="order-3 -mx-4 flex h-11 w-[calc(100%+2rem)] items-stretch gap-0.5 overflow-x-auto scroll-none whitespace-nowrap border-t border-white/25 px-2 md:order-2 md:mx-0 md:ml-auto md:h-14 md:w-auto md:border-t-0 md:px-0"
            aria-label="Main"
          >
            <NavLink to="/" end className={navClass}>Find jobs</NavLink>
            <NavLink to="/resume" className={navClass}>Match my resume</NavLink>
            {me && <NavLink to="/saved" className={navClass}>Tracker</NavLink>}
            <NavLink
              to="/ai-key"
              className={navClass}
              title={aiKey ? 'Your AI key is set' : 'Add your own AI key'}
            >
              AI key
              {aiKey && (
                <span className="ml-1.5 inline-flex items-center gap-1 text-xs font-bold uppercase text-white">
                  <span className="h-2 w-2 rounded-full bg-white" aria-hidden="true" />
                  on
                </span>
              )}
            </NavLink>
            {me?.is_admin && (
              <NavLink to="/admin/sources" className={navClass}>Admin</NavLink>
            )}
            {me && (
              <NavLink to="/account" className={navClass} title={me.is_demo ? undefined : me.email}>
                {me.is_demo ? 'Temporary account' : 'Account'}
              </NavLink>
            )}
          </nav>

          <div className="order-2 ml-auto flex h-14 items-center gap-2 md:order-3 md:ml-0">
            <span className="mx-2 hidden h-6 w-px bg-white/40 md:block" aria-hidden="true" />
            {isLoading ? (
              <div className="h-8 w-24 animate-pulse bg-white/20" />
            ) : me ? (
              <button
                onClick={() => logout.mutate()}
                className="border-2 border-white px-3 py-1 text-sm font-bold text-white hover:bg-white hover:text-post-700"
              >
                Sign out
              </button>
            ) : (
              <>
                <DemoButton variant="header" />
                <Link
                  to={`/sign-in?next=${encodeURIComponent(next)}`}
                  className="border-2 border-white bg-white px-3.5 py-1 text-sm font-bold text-post-700 hover:bg-post-50"
                >
                  Sign in
                </Link>
              </>
            )}
          </div>
        </div>
      </div>

      <DemoBanner />
    </header>
  )
}

export default function App() {
  return (
    <div className="flex min-h-screen flex-col">
      <Header />
      <main className="flex-1">
        <Suspense fallback={<div className="flex h-64 items-center justify-center text-gray-600">Loading...</div>}>
          <Routes>
            <Route path="/" element={<PostingsListPage />} />
            <Route path="/postings/:id" element={<PostingDetailPage />} />
            <Route path="/saved" element={<SavedPostingsPage />} />
            <Route path="/resume" element={<ResumePage />} />
            <Route path="/ai-key" element={<AiKeyPage />} />
            <Route path="/account" element={<AccountSettingsPage />} />
            <Route path="/add" element={<AddPostingsPage />} />
            <Route path="/sign-in" element={<SignInPage />} />
            {/* Old links still land somewhere useful */}
            <Route path="/matches" element={<Navigate to="/resume" replace />} />
            <Route path="/upload" element={<Navigate to="/add" replace />} />
            <Route path="/submit" element={<Navigate to="/add" replace />} />
            <Route path="/admin/sources" element={<AdminSourcesPage />} />
          </Routes>
        </Suspense>
      </main>
      <footer className="border-t border-gray-300 bg-white">
        <div className="flex w-full flex-col gap-3 px-4 py-6 lg:px-6 text-sm text-gray-600 sm:flex-row sm:items-center sm:justify-between">
          <p className="flex items-center gap-2">
            <LogoMark className="h-5 w-5 text-post-600" />
            <span>Jobs come straight from employers' own career pages. You always apply on their site.</span>
          </p>
          <nav className="flex gap-5 font-semibold" aria-label="Footer">
            <Link to="/" className="hover:text-gray-900 hover:underline">Find jobs</Link>
            <Link to="/resume" className="hover:text-gray-900 hover:underline">Match my resume</Link>
            <Link to="/ai-key" className="hover:text-gray-900 hover:underline">AI key</Link>
          </nav>
        </div>
      </footer>
    </div>
  )
}
