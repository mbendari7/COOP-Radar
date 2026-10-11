/**
 * ResumeUploadForm — file input for uploading a resume + stored metadata display.
 *
 * Shows:
 * - When no resume: file input with upload button
 * - When resume exists: filename, size, upload date + Delete button
 * Both views include the upload input so re-uploading is always possible.
 */

import { useRef, useState } from 'react'
import { useDeleteResume, useMatches, useUploadResume } from '../api/resume'
import type { ResumeOut } from '../api/resume'

const MAX_SIZE_BYTES = 5 * 1024 * 1024  // 5 MB

function formatBytes(bytes: number): string {
  if (bytes < 1024) return `${bytes} B`
  if (bytes < 1024 * 1024) return `${(bytes / 1024).toFixed(1)} KB`
  return `${(bytes / (1024 * 1024)).toFixed(1)} MB`
}

function formatDate(iso: string): string {
  return new Date(iso).toLocaleDateString(undefined, {
    year: 'numeric', month: 'short', day: 'numeric',
  })
}

interface Props {
  /** Called after a successful upload so parent can react (optional) */
  onUploaded?: () => void
  /** Called after a successful delete (optional) */
  onDeleted?: () => void
  /** Show the stored-resume card inline (true by default) */
  showStoredCard?: boolean
}

export default function ResumeUploadForm({ onUploaded, onDeleted, showStoredCard = true }: Props) {
  // The matches response carries the stored resume's metadata (null when none)
  const { data: matches } = useMatches()
  const resume: ResumeOut | null = matches?.resume ?? null
  const upload = useUploadResume()
  const deleteResume = useDeleteResume()
  const inputRef = useRef<HTMLInputElement>(null)
  const [clientError, setClientError] = useState<string | null>(null)
  const [deleteConfirm, setDeleteConfirm] = useState(false)

  function handleFile(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0]
    if (!file) return
    setClientError(null)

    const ext = file.name.split('.').pop()?.toLowerCase()
    if (ext !== 'pdf' && ext !== 'docx') {
      setClientError('Only PDF or DOCX files are accepted.')
      return
    }
    if (file.size > MAX_SIZE_BYTES) {
      setClientError(`File is too large (${formatBytes(file.size)}). Maximum is 5 MB.`)
      return
    }

    upload.mutate(file, {
      onSuccess: () => {
        if (inputRef.current) inputRef.current.value = ''
        onUploaded?.()
      },
      onError: (err) => {
        setClientError(err.message || 'Upload failed.')
      },
    })
  }

  const hasResume = resume !== null

  return (
    <div className="space-y-4">
      {/* Stored resume card */}
      {showStoredCard && hasResume && (
        <StoredResumeCard
          resume={resume}
          onDeleteClick={() => setDeleteConfirm(true)}
          isDeleting={deleteResume.isPending}
        />
      )}

      {/* Upload input */}
      <div>
        <label
          htmlFor="resume-file-input"
          className="block text-sm font-medium text-gray-700 mb-1"
        >
          {hasResume ? 'Replace resume' : 'Upload resume'}
        </label>
        <input
          ref={inputRef}
          id="resume-file-input"
          type="file"
          accept=".pdf,.docx"
          onChange={handleFile}
          aria-describedby={clientError ? 'resume-upload-error' : undefined}
          className="block w-full text-sm text-gray-700 file:mr-3 file:py-1.5 file:px-3 file:rounded-md file:border file:border-gray-300 file:text-sm file:font-medium file:bg-white file:text-gray-700 hover:file:bg-gray-50 focus:outline-none"
        />
        <p className="mt-1 text-xs text-gray-400">PDF or DOCX, max 5 MB</p>
      </div>

      {/* Upload errors */}
      {(clientError || upload.error) && (
        <p id="resume-upload-error" role="alert" className="text-sm text-red-600">
          {clientError ?? upload.error?.message}
        </p>
      )}

      {/* Upload loading */}
      {upload.isPending && (
        <p className="text-sm text-gray-500 animate-pulse">
          Uploading and matching… this may take up to 30 seconds.
        </p>
      )}

      {/* Delete confirmation modal */}
      {deleteConfirm && (
        <div
          role="dialog"
          aria-modal="true"
          aria-labelledby="delete-modal-title"
          className="fixed inset-0 z-50 flex items-center justify-center bg-black/40 p-4"
        >
          <div className="bg-white rounded-xl shadow-xl max-w-sm w-full p-6 space-y-4">
            <h2 id="delete-modal-title" className="text-base font-semibold text-gray-900">
              Delete resume?
            </h2>
            <p className="text-sm text-gray-600">
              This will permanently remove your resume and all match results.
            </p>
            <div className="flex gap-3 justify-end">
              <button
                onClick={() => setDeleteConfirm(false)}
                className="px-4 py-2 text-sm rounded-lg border border-gray-300 hover:bg-gray-50"
              >
                Cancel
              </button>
              <button
                onClick={() => {
                  deleteResume.mutate(undefined, {
                    onSuccess: () => {
                      setDeleteConfirm(false)
                      onDeleted?.()
                    },
                  })
                }}
                disabled={deleteResume.isPending}
                className="px-4 py-2 text-sm rounded-lg bg-red-600 text-white hover:bg-red-700 disabled:opacity-50"
              >
                {deleteResume.isPending ? 'Deleting…' : 'Delete resume'}
              </button>
            </div>
          </div>
        </div>
      )}
    </div>
  )
}

function StoredResumeCard({
  resume,
  onDeleteClick,
  isDeleting,
}: {
  resume: ResumeOut
  onDeleteClick: () => void
  isDeleting: boolean
}) {
  return (
    <div className="flex items-center justify-between rounded-lg border border-gray-200 bg-gray-50 px-4 py-3">
      <div className="min-w-0">
        <p className="text-sm font-medium text-gray-900 truncate">{resume.filename}</p>
        <p className="text-xs text-gray-500 mt-0.5">
          {formatBytes(resume.file_size)} · Uploaded {formatDate(resume.uploaded_at)}
        </p>
      </div>
      <button
        onClick={onDeleteClick}
        disabled={isDeleting}
        aria-label="Delete resume"
        className="ml-4 shrink-0 text-sm text-red-600 hover:text-red-800 disabled:opacity-40 focus:outline-none focus:ring-2 focus:ring-red-500 rounded"
      >
        Delete resume
      </button>
    </div>
  )
}
