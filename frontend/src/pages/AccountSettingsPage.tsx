/**
 * AccountSettingsPage — /account route.
 *
 * Two sections: change password and delete account.
 * Delete requires two-step confirmation to prevent accidents.
 */

import { useState } from 'react'
import { changePassword, deleteAccount, useLogout, useMe } from '../api/auth'
import { ApiError } from '../api/client'
import { Link, Navigate, useNavigate } from 'react-router-dom'
import ClaimAccountForm from '../components/ClaimAccountForm'

export default function AccountSettingsPage() {
  const navigate = useNavigate()
  const { data: me, isLoading } = useMe()
  const logout = useLogout()

  // Change password state
  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [pwError, setPwError] = useState<string | null>(null)
  const [pwSuccess, setPwSuccess] = useState(false)
  const [pwLoading, setPwLoading] = useState(false)

  // Delete account state
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deletePassword, setDeletePassword] = useState('')
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [deleteLoading, setDeleteLoading] = useState(false)

  if (isLoading) {
    return <div className="flex justify-center items-center h-64 text-gray-500">Loading...</div>
  }

  if (!me) {
    return <Navigate to="/" replace />
  }

  const handleChangePassword = async (e: React.FormEvent) => {
    e.preventDefault()
    setPwError(null)
    setPwSuccess(false)
    setPwLoading(true)

    try {
      await changePassword(currentPw, newPw)
      setPwSuccess(true)
      setCurrentPw('')
      setNewPw('')
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setPwError('Current password is incorrect.')
      } else if (err instanceof ApiError && err.status === 422) {
        setPwError('New password must be at least 10 characters.')
      } else {
        setPwError('Something went wrong. Please try again.')
      }
    } finally {
      setPwLoading(false)
    }
  }

  const handleDeleteAccount = async (e: React.FormEvent) => {
    e.preventDefault()
    setDeleteError(null)
    setDeleteLoading(true)

    try {
      await deleteAccount(deletePassword)
      // Account deleted — clear cached data and go home
      await logout.mutateAsync().catch(() => undefined)
      navigate('/')
    } catch (err) {
      if (err instanceof ApiError && err.status === 401) {
        setDeleteError('Password is incorrect.')
      } else {
        setDeleteError('Something went wrong. Please try again.')
      }
    } finally {
      setDeleteLoading(false)
    }
  }

  if (me.is_demo) {
    return (
      <div className="max-w-lg mx-auto px-4 py-10 space-y-6">
        <h1 className="text-2xl font-semibold text-gray-900">Temporary account</h1>
        <p className="text-sm text-gray-600">
          This account is private to you and is deleted automatically 7 days after it was created.
          Add an email and password to keep it. Your resume, matches and tracker all stay.
        </p>
        <ClaimAccountForm />
        <p className="text-sm text-gray-500">
          Not keeping it? Just sign out. Everything is removed when it expires.
        </p>
      </div>
    )
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-10">
      <h1 className="text-2xl font-semibold text-gray-900 mb-8">Account Settings</h1>
      <p className="text-sm text-gray-500 mb-8">{me.email}</p>

      {/* ── Change Password ── */}
      <section className="mb-10">
        <h2 className="text-lg font-medium text-gray-900 mb-4">Change Password</h2>
        <form onSubmit={handleChangePassword} className="space-y-4">
          <div>
            <label htmlFor="current-pw" className="block text-sm font-medium text-gray-700 mb-1">
              Current password
            </label>
            <input
              id="current-pw"
              type="password"
              autoComplete="current-password"
              required
              value={currentPw}
              onChange={(e) => setCurrentPw(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          <div>
            <label htmlFor="new-pw" className="block text-sm font-medium text-gray-700 mb-1">
              New password <span className="text-gray-500 font-normal">(min 10 characters)</span>
            </label>
            <input
              id="new-pw"
              type="password"
              autoComplete="new-password"
              required
              minLength={10}
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
            />
          </div>
          {pwError && <p role="alert" className="text-sm text-red-600">{pwError}</p>}
          {pwSuccess && <p role="status" className="text-sm text-green-600">Password updated successfully.</p>}
          <button
            type="submit"
            disabled={pwLoading}
            className="px-4 py-2 bg-blue-600 text-white text-sm font-medium rounded-lg hover:bg-blue-700 disabled:opacity-50"
          >
            {pwLoading ? 'Updating...' : 'Update password'}
          </button>
        </form>
      </section>

      <hr className="border-gray-200 mb-10" />

      {/* ── Resume ── */}
      <section className="mb-10">
        <h2 className="text-lg font-medium text-gray-900 mb-2">Resume</h2>
        <p className="text-sm text-gray-600">
          Upload, replace, or delete your resume on <Link to="/resume" className="text-blue-700 hover:underline">My resume</Link>.
        </p>
      </section>

      <hr className="border-gray-200 mb-10" />

      {/* ── Delete Account ── */}
      <section>
        <h2 className="text-lg font-medium text-red-700 mb-2">Delete Account</h2>
        <p className="text-sm text-gray-500 mb-4">
          This permanently removes your account and all saved postings. This action cannot be undone.
        </p>

        {!showDeleteConfirm ? (
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="px-4 py-2 border border-red-300 text-red-600 text-sm font-medium rounded-lg hover:bg-red-50"
          >
            Delete my account
          </button>
        ) : (
          <form onSubmit={handleDeleteAccount} className="space-y-4 border border-red-200 rounded-lg p-4 bg-red-50">
            <p className="text-sm font-medium text-red-700">
              Enter your password to confirm deletion.
            </p>
            <input
              type="password"
              autoComplete="current-password"
              required
              placeholder="Your password"
              value={deletePassword}
              onChange={(e) => setDeletePassword(e.target.value)}
              className="w-full rounded-lg border border-red-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-red-500"
            />
            {deleteError && <p role="alert" className="text-sm text-red-700">{deleteError}</p>}
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={deleteLoading}
                className="px-4 py-2 bg-red-600 text-white text-sm font-medium rounded-lg hover:bg-red-700 disabled:opacity-50"
              >
                {deleteLoading ? 'Deleting...' : 'Permanently delete account'}
              </button>
              <button
                type="button"
                onClick={() => { setShowDeleteConfirm(false); setDeleteError(null) }}
                className="px-4 py-2 border border-gray-300 text-gray-600 text-sm rounded-lg hover:bg-gray-50"
              >
                Cancel
              </button>
            </div>
          </form>
        )}
      </section>
    </div>
  )
}
