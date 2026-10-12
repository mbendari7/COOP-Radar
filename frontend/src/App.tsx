/**
 * App root: router, header, footer and routes.
 *
 * Main nav (everyone): Jobs · Match my resume · Tracker · AI key
 * Right side: signed in → account link + "Sign out"; signed out → "Try the demo" + "Sign in".
 * Temporary (guest/demo) accounts get a banner offering to keep the account.
 */

import { lazy, Suspense, useState } from 'react'
import { Link, NavLink, Navigate, Route, Routes } from 'react-router-dom'
import { useAiKey } from './api/aiKey'
import { useMe, useLogout } from './api/auth'
import AuthModal from './components/AuthModal'
import DemoBanner from './components/DemoBanner'
import DemoButton from './components/DemoButton'
import { LogoMark } from './components/Icons'
import PostingDetailPage from './pages/PostingDetailPage'
import PostingsListPage from './pages/PostingsListPage'

// Lazy-load heavy pages so the initial bundle stays small
const ResumePage = lazy(() => import('./pages/ResumePage'))
const AiKeyPage = lazy(() => import('./pages/AiKeyPage'))
const SavedPostingsPage = lazy(() => import('./pages/SavedPostingsPage'))
const AccountSettingsPage = lazy(() => import('./pages/AccountSettingsPage'))
const AdminSourcesPage = lazy(() =>
  import('./pages/AdminSourcesPage').then((m) => ({ default: m.AdminSourcesPage }))
)
const CsvUploadPage = lazy(() =>
  import('./components/CsvUploadForm').then((m) => ({ default: m.CsvUploadForm }))
)
const ManualPostingPage = lazy(() =>
  import('./components/ManualPostingForm').then((m) => ({ default: m.ManualPostingForm }))
)

/** CSV bulk import and single-posting form on one page. */
function AddPostingsPage() {
  return (
    <div className="p-6 max-w-2xl mx-auto space-y-12">
      <CsvUploadPage />
      <ManualPostingPage />
    </div>
  )
}

/** Job-board style tabs: the current page is underlined in the accent colour. */
function navClass({ isActive }: { isActive: boolean }): string {
  return `flex h-16 items-center border-b-2 px-2.5 text-sm font-medium ${
    isActive ? 'border-blue-600 text-gray-900' : 'border-transparent text-gray-600 hover:text-gray-900'
  }`
}

function Header() {
  const { data: me, isLoading } = useMe()
  const aiKey = useAiKey()
  const logout = useLogout()
  const [authOpen, setAuthOpen] = useState(false)

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
      <div className="max-w-7xl mx-auto px-4 h-16 flex items-center justify-between gap-4">
        <Link to="/" className="flex items-center gap-2 shrink-0" aria-label="CoopRadar home">
          <LogoMark />
          <span className="text-lg font-bold tracking-tight text-gray-900">CoopRadar</span>
        </Link>

        {/* Scrolls sideways on narrow phones instead of overflowing the page */}
        <nav className="flex h-16 items-center gap-1 sm:gap-2 overflow-x-auto whitespace-nowrap" aria-label="Main">
          <NavLink to="/" end className={navClass}>Find jobs</NavLink>
          <NavLink to="/resume" className={navClass}>Match my resume</NavLink>
          {me && <NavLink to="/saved" className={navClass}>Tracker</NavLink>}
          <NavLink
            to="/ai-key"
            className={({ isActive }) =>
              navClass({ isActive }) + (aiKey && !isActive ? ' !text-green-700' : '')
            }
            title={aiKey ? 'Your AI key is set' : 'Add your own AI key'}
          >
            {aiKey ? 'AI key (on)' : 'AI key'}
          </NavLink>
          {me?.is_admin && (
            <NavLink to="/admin/sources" className={navClass}>Admin</NavLink>
          )}

          <span className="mx-1 h-5 w-px bg-gray-200" aria-hidden="true" />

          {isLoading ? (
            <div className="h-8 w-24 bg-gray-100 rounded animate-pulse" />
          ) : me ? (
            <>
              <NavLink to="/account" className={navClass} title={me.is_demo ? undefined : me.email}>
                {me.is_demo ? 'Temporary account' : 'Account'}
              </NavLink>
              <button
                onClick={() => logout.mutate()}
                className="text-sm text-gray-700 hover:text-gray-900 px-3 py-1.5 border border-gray-300 rounded-md hover:bg-gray-50"
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <DemoButton variant="header" />
              <button
                onClick={() => setAuthOpen(true)}
                className="text-sm font-semibold px-3.5 py-1.5 bg-blue-600 text-white rounded-md hover:bg-blue-700"
              >
                Sign in
              </button>
            </>
          )}
        </nav>
      </div>

      <AuthModal open={authOpen} onClose={() => setAuthOpen(false)} initialTab="login" />
      <DemoBanner />
    </header>
  )
}

export default function App() {
  return (
    <div className="min-h-screen flex flex-col">
      <Header />
      <main className="flex-1">
        <Suspense fallback={<div className="flex justify-center items-center h-64 text-gray-500">Loading...</div>}>
          <Routes>
            <Route path="/" element={<PostingsListPage />} />
            <Route path="/postings/:id" element={<PostingDetailPage />} />
            <Route path="/saved" element={<SavedPostingsPage />} />
            <Route path="/resume" element={<ResumePage />} />
            <Route path="/ai-key" element={<AiKeyPage />} />
            <Route path="/account" element={<AccountSettingsPage />} />
            <Route path="/add" element={<AddPostingsPage />} />
            {/* Older links */}
            <Route path="/matches" element={<Navigate to="/resume" replace />} />
            <Route path="/upload" element={<Navigate to="/add" replace />} />
            <Route path="/submit" element={<Navigate to="/add" replace />} />
            <Route path="/admin/sources" element={<AdminSourcesPage />} />
          </Routes>
        </Suspense>
      </main>
      <footer className="border-t border-gray-200 bg-white">
        <div className="max-w-7xl mx-auto px-4 py-6 flex flex-col sm:flex-row gap-2 sm:items-center sm:justify-between text-sm text-gray-500">
          <p>CoopRadar. Jobs come from employers' public career pages. Always apply on the employer's site.</p>
          <nav className="flex gap-4" aria-label="Footer">
            <Link to="/" className="hover:text-gray-800">Find jobs</Link>
            <Link to="/resume" className="hover:text-gray-800">Match my resume</Link>
            <Link to="/ai-key" className="hover:text-gray-800">AI key</Link>
          </nav>
        </div>
      </footer>
    </div>
  )
}
