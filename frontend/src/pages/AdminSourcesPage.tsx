/**
 * The admin page at /admin/sources. Every place we import jobs from, how its last run went,
 * a button to run it now and its run history. Only admins can open it.
 */

import { useState } from 'react'
import {
  useAdminSources,
  useTriggerRun,
  usePatchSource,
  useRunHistory,
  type IngestSourceOut,
} from '../api/ingest'

function StatusBadge({ status }: { status: string | null }) {
  if (!status) return null
  const colours: Record<string, string> = {
    success: 'bg-air-700 text-white',
    partial: 'border border-air-700 text-air-700',
    failed: 'bg-post-600 text-white',
    running: 'border border-gray-500 text-gray-800',
  }
  return (
    <span className={`inline-flex items-center rounded-sm px-1.5 py-px text-[11px] font-bold uppercase tracking-wide ${colours[status] ?? 'bg-gray-100 text-gray-700'}`}>
      {status}
    </span>
  )
}

function RunHistoryPanel({ sourceId }: { sourceId: string }) {
  const { data, isLoading } = useRunHistory(sourceId)

  if (isLoading) return <p className="text-xs text-gray-600 py-2">Loading history...</p>
  if (!data?.items.length) return <p className="text-xs text-gray-600 py-2">No runs yet.</p>

  return (
    <div className="overflow-x-auto mt-2">
      <table className="w-full text-xs">
        <thead>
          <tr className="label-form border-b border-gray-300">
            <th className="text-left px-2 py-1">Started</th>
            <th className="text-left px-2 py-1">Status</th>
            <th className="text-right px-2 py-1">Added</th>
            <th className="text-right px-2 py-1">Errors</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((run) => (
            <tr key={run.id} className="border-t border-gray-200">
              <td className="px-2 py-1">{new Date(run.started_at).toLocaleString()}</td>
              <td className="px-2 py-1"><StatusBadge status={run.status} /></td>
              <td className="px-2 py-1 text-right">{run.added}</td>
              <td className={`px-2 py-1 text-right ${run.errors > 0 ? 'font-bold text-post-600' : ''}`}>
                {run.errors}
              </td>
            </tr>
          ))}
        </tbody>
      </table>
    </div>
  )
}

function SourceCard({ source }: { source: IngestSourceOut }) {
  const [expanded, setExpanded] = useState(false)
  const trigger = useTriggerRun()
  const patch = usePatchSource()

  const isRunning = source.last_run_status === 'running'

  return (
    <div className="border-b border-gray-300 py-4">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-medium text-gray-900">{source.name}</h3>
            <span className="label-form rounded-sm border border-gray-400 px-1.5 py-px">
              {source.adapter_type}
            </span>
            {source.auto_paused && (
              <span className="label-form rounded-sm bg-post-600 px-1.5 py-px !text-white">
                Paused itself
              </span>
            )}
            {!source.enabled && !source.auto_paused && (
              <span className="label-form rounded-sm bg-gray-200 px-1.5 py-px">
                Disabled
              </span>
            )}
          </div>
          {source.last_run_at && (
            <p className="mt-1 text-xs text-gray-600">
              Last run {new Date(source.last_run_at).toLocaleString()} ·{' '}
              <StatusBadge status={source.last_run_status} />
            </p>
          )}
          <div className="mt-1 flex gap-3 text-xs text-gray-600">
            {source.last_run_added !== null && <span>+{source.last_run_added} added</span>}
            {source.last_run_closed !== null && source.last_run_closed > 0 && (
              <span>{source.last_run_closed} closed</span>
            )}
            {source.last_run_errors !== null && source.last_run_errors > 0 && (
              <span className="font-bold text-post-600">{source.last_run_errors} errors</span>
            )}
          </div>
        </div>

        <div className="flex gap-2 shrink-0">
          {source.auto_paused ? (
            <button
              onClick={() => patch.mutate({ sourceId: source.id, data: { auto_paused: false, enabled: true } })}
              disabled={patch.isPending}
              className="btn-primary px-3 py-1 text-xs"
            >
              Turn back on
            </button>
          ) : (
            <button
              onClick={() => trigger.mutate(source.id)}
              disabled={isRunning || trigger.isPending || !source.enabled}
              className="btn-primary px-3 py-1 text-xs"
            >
              {isRunning ? 'Running...' : 'Run now'}
            </button>
          )}
          <button
            onClick={() => setExpanded((v) => !v)}
            className="btn-secondary px-3 py-1 text-xs"
            aria-expanded={expanded}
          >
            {expanded ? 'Hide history' : 'History'}
          </button>
        </div>
      </div>

      {expanded && <RunHistoryPanel sourceId={source.id} />}
    </div>
  )
}

export function AdminSourcesPage() {
  const { data, isLoading, isError } = useAdminSources()

  if (isLoading) {
    return (
      <main className="p-6 max-w-4xl mx-auto">
        <div className="space-y-4">
          {[...Array(3)].map((_, i) => (
            <div key={i} className="h-24 animate-pulse bg-gray-100" />
          ))}
        </div>
      </main>
    )
  }

  if (isError) {
    return (
      <main className="p-6 max-w-4xl mx-auto">
        <div role="alert" className="border-[1.5px] border-post-600 p-4 text-sm font-semibold text-post-700">
          The sources didn't load. You might not have admin access.
        </div>
      </main>
    )
  }

  return (
    <main className="p-6 max-w-4xl mx-auto">
      <h1 className="display mb-6 text-4xl text-gray-900">Import sources</h1>

      {!data?.length ? (
        <p className="text-gray-500">No sources set up yet.</p>
      ) : (
        <div className="space-y-4">
          {data.map((source) => (
            <SourceCard key={source.id} source={source} />
          ))}
        </div>
      )}
    </main>
  )
}
