/**
 * Your account at /account.
 *
 * Change your password or delete the account.
 * Deleting asks twice so nobody does it by accident.
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

  // Changing the password
  const [currentPw, setCurrentPw] = useState('')
  const [newPw, setNewPw] = useState('')
  const [pwError, setPwError] = useState<string | null>(null)
  const [pwSuccess, setPwSuccess] = useState(false)
  const [pwLoading, setPwLoading] = useState(false)

  // Deleting the account
  const [showDeleteConfirm, setShowDeleteConfirm] = useState(false)
  const [deletePassword, setDeletePassword] = useState('')
  const [deleteError, setDeleteError] = useState<string | null>(null)
  const [deleteLoading, setDeleteLoading] = useState(false)

  if (isLoading) {
    return <div className="flex h-64 items-center justify-center text-gray-600">Loading...</div>
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
      // The account is gone so clear what we cached and go home
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
        <h1 className="display text-4xl text-gray-900">Temporary account</h1>
        <p className="text-sm text-gray-700">
          This account is private to you and is deleted automatically 7 days after it was created.
          Add an email and password to keep it. Your resume, matches and tracker all stay.
        </p>
        <ClaimAccountForm />
        <p className="text-sm text-gray-700">
          Not keeping it? Just sign out. Everything is removed when it expires.
        </p>
      </div>
    )
  }

  return (
    <div className="max-w-lg mx-auto px-4 py-10">
      <h1 className="display mb-2 text-4xl text-gray-900">Account</h1>
      <p className="text-sm text-gray-700 mb-8">{me.email}</p>

      {/* Change password */}
      <section className="mb-10">
        <h2 className="display mb-4 text-2xl text-gray-900">Change password</h2>
        <form onSubmit={handleChangePassword} className="space-y-4">
          <div>
            <label htmlFor="current-pw" className="label-form mb-1 block !text-gray-900">
              Current password
            </label>
            <input
              id="current-pw"
              type="password"
              autoComplete="current-password"
              required
              value={currentPw}
              onChange={(e) => setCurrentPw(e.target.value)}
              className="field"
            />
          </div>
          <div>
            <label htmlFor="new-pw" className="label-form mb-1 block !text-gray-900">
              New password <span className="font-normal normal-case tracking-normal text-gray-600">10 characters or more</span>
            </label>
            <input
              id="new-pw"
              type="password"
              autoComplete="new-password"
              required
              minLength={10}
              value={newPw}
              onChange={(e) => setNewPw(e.target.value)}
              className="field"
            />
          </div>
          {pwError && <p role="alert" className="text-sm font-semibold text-post-700">{pwError}</p>}
          {pwSuccess && <p role="status" className="text-sm font-semibold text-air-700">Password updated.</p>}
          <button
            type="submit"
            disabled={pwLoading}
            className="btn-primary"
          >
            {pwLoading ? 'Updating...' : 'Update password'}
          </button>
        </form>
      </section>

      <hr className="mb-10 border-gray-300" />

      {/* Resume */}
      <section className="mb-10">
        <h2 className="display mb-2 text-2xl text-gray-900">Resume</h2>
        <p className="text-sm text-gray-700">
          Upload, replace or delete your resume on <Link to="/resume" className="link">Match my resume</Link>.
        </p>
      </section>

      <hr className="mb-10 border-gray-300" />

      {/* Delete account */}
      <section>
        <h2 className="display mb-2 text-2xl text-post-700">Delete account</h2>
        <p className="text-sm text-gray-700 mb-4">
          This removes your account and every saved job for good. You cannot undo it.
        </p>

        {!showDeleteConfirm ? (
          <button
            onClick={() => setShowDeleteConfirm(true)}
            className="btn border-post-600 bg-white text-post-700 hover:bg-post-50"
          >
            Delete my account
          </button>
        ) : (
          <form onSubmit={handleDeleteAccount} className="space-y-4 border-[1.5px] border-post-600 bg-post-50 p-4">
            <p className="text-sm font-bold text-post-700">
              Enter your password to confirm deletion.
            </p>
            <input
              type="password"
              autoComplete="current-password"
              required
              placeholder="Your password"
              value={deletePassword}
              onChange={(e) => setDeletePassword(e.target.value)}
              className="field border-post-600"
            />
            {deleteError && <p role="alert" className="text-sm font-semibold text-post-700">{deleteError}</p>}
            <div className="flex gap-3">
              <button
                type="submit"
                disabled={deleteLoading}
                className="btn-primary"
              >
                {deleteLoading ? 'Deleting...' : 'Permanently delete account'}
              </button>
              <button
                type="button"
                onClick={() => { setShowDeleteConfirm(false); setDeleteError(null) }}
                className="btn-secondary"
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
