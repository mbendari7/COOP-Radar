/**
 * App root — router, header with auth slot, and routes.
 *
 * The header shows:
 * - Loading: skeleton placeholder
 * - Authenticated: Saved / Matches / Add postings (+ Admin) links, account link, "Sign out"
 * - Unauthenticated: "Sign in / Register" button that opens AuthModal
 */

import { lazy, Suspense, useState } from 'react'
import { Link, Navigate, Route, Routes } from 'react-router-dom'
import { useMe, useLogout } from './api/auth'
import AuthModal from './components/AuthModal'
import PostingDetailPage from './pages/PostingDetailPage'
import PostingsListPage from './pages/PostingsListPage'

// Lazy-load heavy pages so the initial bundle stays small
const MatchResultsPage = lazy(() => import('./pages/MatchResultsPage'))
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

function Header() {
  const { data: me, isLoading } = useMe()
  const logout = useLogout()
  const [authOpen, setAuthOpen] = useState(false)
  const [authTab, setAuthTab] = useState<'register' | 'login'>('register')

  const openAuth = (tab: 'register' | 'login') => {
    setAuthTab(tab)
    setAuthOpen(true)
  }

  return (
    <header className="bg-white border-b border-gray-200 sticky top-0 z-30">
      <div className="max-w-6xl mx-auto px-4 h-14 flex items-center justify-between gap-4">
        <Link to="/" className="text-lg font-bold text-blue-700 tracking-tight hover:text-blue-800">
          CoopRadar
        </Link>

        <nav className="flex items-center gap-3">
          {isLoading ? (
            <div className="h-8 w-32 bg-gray-100 rounded animate-pulse" />
          ) : me ? (
            <>
              <Link
                to="/saved"
                className="text-sm text-gray-600 hover:text-gray-900 font-medium"
              >
                Saved
              </Link>
              <Link
                to="/matches"
                className="text-sm text-gray-600 hover:text-gray-900 font-medium"
              >
                Matches
              </Link>
              <Link
                to="/add"
                className="text-sm text-gray-600 hover:text-gray-900 font-medium"
              >
                Add postings
              </Link>
              {me.is_admin && (
                <Link
                  to="/admin/sources"
                  className="text-sm text-amber-700 hover:text-amber-900 font-medium"
                >
                  Admin
                </Link>
              )}
              <Link
                to="/account"
                className="text-sm text-gray-500 hover:text-gray-900"
              >
                {me.email}
              </Link>
              <button
                onClick={() => logout.mutate()}
                className="text-sm text-gray-500 hover:text-gray-700 px-3 py-1.5 border border-gray-200 rounded-lg hover:bg-gray-50"
              >
                Sign out
              </button>
            </>
          ) : (
            <>
              <button
                onClick={() => openAuth('login')}
                className="text-sm text-gray-600 hover:text-gray-900 font-medium"
              >
                Sign in
              </button>
              <button
                onClick={() => openAuth('register')}
                className="text-sm font-medium px-3 py-1.5 bg-blue-600 text-white rounded-lg hover:bg-blue-700"
              >
                Register
              </button>
            </>
          )}
        </nav>
      </div>

      <AuthModal
        open={authOpen}
        onClose={() => setAuthOpen(false)}
        initialTab={authTab}
      />
    </header>
  )
}

export default function App() {
  return (
    <div className="min-h-screen bg-gray-50">
      <Header />
      <main>
        <Suspense fallback={<div className="flex justify-center items-center h-64 text-gray-400">Loading…</div>}>
          <Routes>
            <Route path="/" element={<PostingsListPage />} />
            <Route path="/postings/:id" element={<PostingDetailPage />} />
            <Route path="/saved" element={<SavedPostingsPage />} />
            <Route path="/matches" element={<MatchResultsPage />} />
            <Route path="/account" element={<AccountSettingsPage />} />
            <Route path="/add" element={<AddPostingsPage />} />
            {/* Older links */}
            <Route path="/upload" element={<Navigate to="/add" replace />} />
            <Route path="/submit" element={<Navigate to="/add" replace />} />
            <Route path="/admin/sources" element={<AdminSourcesPage />} />
          </Routes>
        </Suspense>
      </main>
    </div>
  )
}
