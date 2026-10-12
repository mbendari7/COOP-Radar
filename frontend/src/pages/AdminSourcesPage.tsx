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
    success: 'bg-green-100 text-green-800',
    partial: 'bg-yellow-100 text-yellow-800',
    failed: 'bg-red-100 text-red-800',
    running: 'bg-blue-100 text-blue-800',
  }
  return (
    <span className={`inline-flex items-center rounded-full px-2 py-0.5 text-xs font-medium ${colours[status] ?? 'bg-gray-100 text-gray-700'}`}>
      {status}
    </span>
  )
}

function RunHistoryPanel({ sourceId }: { sourceId: string }) {
  const { data, isLoading } = useRunHistory(sourceId)

  if (isLoading) return <p className="text-xs text-gray-500 py-2">Loading history...</p>
  if (!data?.items.length) return <p className="text-xs text-gray-500 py-2">No runs yet.</p>

  return (
    <div className="overflow-x-auto mt-2">
      <table className="w-full text-xs">
        <thead>
          <tr className="bg-gray-50 text-gray-500">
            <th className="text-left px-2 py-1">Started</th>
            <th className="text-left px-2 py-1">Status</th>
            <th className="text-right px-2 py-1">Added</th>
            <th className="text-right px-2 py-1">Errors</th>
          </tr>
        </thead>
        <tbody>
          {data.items.map((run) => (
            <tr key={run.id} className="border-t border-gray-100">
              <td className="px-2 py-1">{new Date(run.started_at).toLocaleString()}</td>
              <td className="px-2 py-1"><StatusBadge status={run.status} /></td>
              <td className="px-2 py-1 text-right">{run.added}</td>
              <td className={`px-2 py-1 text-right ${run.errors > 0 ? 'text-red-600 font-medium' : ''}`}>
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
    <div className="rounded-lg border border-gray-200 bg-white p-4 shadow-sm">
      <div className="flex items-start justify-between gap-4">
        <div>
          <div className="flex items-center gap-2 flex-wrap">
            <h3 className="font-medium text-gray-900">{source.name}</h3>
            <span className="rounded bg-gray-100 px-1.5 py-0.5 text-xs text-gray-600">
              {source.adapter_type}
            </span>
            {source.auto_paused && (
              <span className="rounded bg-amber-100 px-1.5 py-0.5 text-xs text-amber-800 font-medium">
                Auto-paused
              </span>
            )}
            {!source.enabled && !source.auto_paused && (
              <span className="rounded bg-gray-200 px-1.5 py-0.5 text-xs text-gray-600">
                Disabled
              </span>
            )}
          </div>
          {source.last_run_at && (
            <p className="mt-1 text-xs text-gray-500">
              Last run: {new Date(source.last_run_at).toLocaleString()} ·{' '}
              <StatusBadge status={source.last_run_status} />
            </p>
          )}
          <div className="mt-1 flex gap-3 text-xs text-gray-500">
            {source.last_run_added !== null && <span>+{source.last_run_added} added</span>}
            {source.last_run_closed !== null && source.last_run_closed > 0 && (
              <span>{source.last_run_closed} closed</span>
            )}
            {source.last_run_errors !== null && source.last_run_errors > 0 && (
              <span className="text-red-600 font-medium">{source.last_run_errors} errors</span>
            )}
          </div>
        </div>

        <div className="flex gap-2 shrink-0">
          {source.auto_paused ? (
            <button
              onClick={() => patch.mutate({ sourceId: source.id, data: { auto_paused: false, enabled: true } })}
              disabled={patch.isPending}
              className="rounded-md bg-amber-600 px-3 py-1.5 text-xs text-white hover:bg-amber-700 disabled:opacity-50"
            >
              Re-enable
            </button>
          ) : (
            <button
              onClick={() => trigger.mutate(source.id)}
              disabled={isRunning || trigger.isPending || !source.enabled}
              className="rounded-md bg-blue-600 px-3 py-1.5 text-xs text-white hover:bg-blue-700 disabled:opacity-50 disabled:cursor-not-allowed"
            >
              {isRunning ? 'Running...' : 'Run now'}
            </button>
          )}
          <button
            onClick={() => setExpanded((v) => !v)}
            className="rounded-md border border-gray-300 px-3 py-1.5 text-xs text-gray-700 hover:bg-gray-50"
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
            <div key={i} className="animate-pulse rounded-lg bg-gray-100 h-24" />
          ))}
        </div>
      </main>
    )
  }

  if (isError) {
    return (
      <main className="p-6 max-w-4xl mx-auto">
        <div role="alert" className="rounded-md bg-red-50 p-4 text-sm text-red-700">
          Failed to load sources. You may not have admin access.
        </div>
      </main>
    )
  }

  return (
    <main className="p-6 max-w-4xl mx-auto">
      <h1 className="text-2xl font-bold text-gray-900 mb-6">Ingest Sources</h1>

      {!data?.length ? (
        <p className="text-gray-500">No sources configured.</p>
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
