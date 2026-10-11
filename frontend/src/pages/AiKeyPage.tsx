/**
 * AiKeyPage — /ai-key
 *
 * Visitors bring their own AI key (Claude, ChatGPT, or Gemini):
 *   1. pick a provider and follow the short "how to get a key" steps
 *   2. paste the key and press "Check key" (the server asks the provider which models it can use)
 *   3. pick a model and save — the key stays in this browser only
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import {
  PROVIDER_GUIDES,
  clearAiKey,
  providerName,
  saveAiKey,
  useAiKey,
  useCheckAiKey,
  type AiKeyCheckResult,
  type AiProvider,
} from '../api/aiKey'
import { usePublicConfig } from '../api/meta'

function mask(key: string): string {
  return key.length <= 8 ? '••••' : `${key.slice(0, 4)}••••${key.slice(-4)}`
}

export default function AiKeyPage() {
  const saved = useAiKey()
  const { data: config } = usePublicConfig()
  const check = useCheckAiKey()

  const [provider, setProvider] = useState<AiProvider>(saved?.provider ?? 'gemini')
  const [apiKey, setApiKey] = useState('')
  const [checked, setChecked] = useState<AiKeyCheckResult | null>(null)
  const [model, setModel] = useState('')
  const [remember, setRemember] = useState(false)
  const [justSaved, setJustSaved] = useState(false)

  const guide = PROVIDER_GUIDES.find((g) => g.id === provider)!

  function chooseProvider(next: AiProvider) {
    setProvider(next)
    setChecked(null)
    setModel('')
    setJustSaved(false)
    check.reset()
  }

  function handleCheck(e: React.FormEvent) {
    e.preventDefault()
    setJustSaved(false)
    check.mutate(
      { provider, api_key: apiKey.trim() },
      {
        onSuccess: (result) => {
          setChecked(result)
          setModel(result.recommended ?? result.models[0]?.id ?? '')
        },
      },
    )
  }

  function handleSave() {
    saveAiKey({ provider, apiKey: apiKey.trim(), model, remember })
    setApiKey('')
    setChecked(null)
    setJustSaved(true)
  }

  return (
    <div className="max-w-3xl mx-auto px-4 py-8 space-y-8">
      <header>
        <h1 className="text-2xl font-bold text-gray-900">Your AI key</h1>
        <p className="mt-2 text-gray-600">
          CoopRadar's AI features — ranking postings against your resume and answering questions about
          them — run on <strong>your own</strong> AI account. Pick a provider, get a key in a couple of
          minutes, and paste it here.
        </p>
        {config?.server_ai_enabled && (
          <p className="mt-2 text-sm text-gray-500">
            This site also has a shared key (limited to {config.ai_daily_limit || 'unlimited'} AI actions a
            day per person), so adding your own is optional.
          </p>
        )}
      </header>

      {/* Current key */}
      {saved && (
        <section className="rounded-xl border border-green-200 bg-green-50 p-4 flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-sm font-semibold text-green-900">
              ✓ Using your {providerName(saved.provider)} key ({mask(saved.apiKey)})
            </p>
            <p className="text-sm text-green-800">
              Model: <code>{saved.model}</code> · {saved.remember ? 'remembered on this device' : 'until you close this tab'}
            </p>
            {justSaved && (
              <p className="mt-1 text-sm text-green-800">
                Saved. Head to <Link to="/matches" className="underline font-medium">Matches</Link> to upload your resume.
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={() => { clearAiKey(); setJustSaved(false) }}
            className="px-3 py-1.5 text-sm rounded-lg border border-green-300 text-green-900 hover:bg-green-100"
          >
            Remove key
          </button>
        </section>
      )}

      {/* Step 1: provider */}
      <section aria-labelledby="step1">
        <h2 id="step1" className="text-lg font-semibold text-gray-900">1. Choose your AI</h2>
        <div className="mt-3 grid gap-3 sm:grid-cols-3" role="radiogroup" aria-label="AI provider">
          {PROVIDER_GUIDES.map((g) => (
            <button
              key={g.id}
              type="button"
              role="radio"
              aria-checked={provider === g.id}
              onClick={() => chooseProvider(g.id)}
              className={`rounded-xl border p-4 text-left focus:outline-none focus:ring-2 focus:ring-blue-500 ${
                provider === g.id ? 'border-blue-600 bg-blue-50' : 'border-gray-200 bg-white hover:border-gray-300'
              }`}
            >
              <span className="block font-semibold text-gray-900">{g.name}</span>
              <span className="block text-sm text-gray-500">by {g.company}</span>
            </button>
          ))}
        </div>
      </section>

      {/* Step 2: how to get a key */}
      <section aria-labelledby="step2" className="rounded-xl border border-gray-200 bg-white p-5">
        <h2 id="step2" className="text-lg font-semibold text-gray-900">2. Get a {guide.name} API key</h2>
        <ol className="mt-3 list-decimal pl-5 space-y-1 text-gray-700">
          {guide.steps.map((step) => <li key={step}>{step}</li>)}
        </ol>
        <a
          href={guide.consoleUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="mt-3 inline-flex items-center gap-1 text-sm font-medium text-blue-700 hover:underline"
        >
          Open the {guide.company} key page <span aria-hidden="true">↗</span>
        </a>
        <p className="mt-3 text-sm text-gray-500"><strong>Cost:</strong> {guide.cost}</p>
      </section>

      {/* Step 3: paste + check */}
      <section aria-labelledby="step3">
        <h2 id="step3" className="text-lg font-semibold text-gray-900">3. Paste it and check it</h2>
        <form onSubmit={handleCheck} className="mt-3 flex flex-col sm:flex-row gap-2">
          <label htmlFor="ai-key" className="sr-only">{guide.name} API key</label>
          <input
            id="ai-key"
            type="password"
            autoComplete="off"
            spellCheck={false}
            placeholder={`Paste your ${guide.name} key (${guide.keyPrefix})`}
            value={apiKey}
            onChange={(e) => { setApiKey(e.target.value); setChecked(null) }}
            className="flex-1 rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
          />
          <button
            type="submit"
            disabled={apiKey.trim().length < 8 || check.isPending}
            className="px-4 py-2 rounded-lg bg-blue-600 text-white text-sm font-medium hover:bg-blue-700 disabled:opacity-50"
          >
            {check.isPending ? 'Checking…' : 'Check key'}
          </button>
        </form>
        {check.isError && (
          <p role="alert" className="mt-2 text-sm text-red-600">{check.error.message}</p>
        )}

        {checked && (
          <div className="mt-4 rounded-xl border border-gray-200 bg-white p-4 space-y-3">
            <p className="text-sm text-green-700 font-medium">
              ✓ Key works — {checked.models.length} model{checked.models.length === 1 ? '' : 's'} available.
            </p>
            {checked.models.length > 0 ? (
              <>
                <div>
                  <label htmlFor="ai-model" className="block text-sm font-medium text-gray-700 mb-1">
                    Model <span className="font-normal text-gray-400">(we pre-selected a good default)</span>
                  </label>
                  <select
                    id="ai-model"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="w-full rounded-lg border border-gray-300 px-3 py-2 text-sm focus:outline-none focus:ring-2 focus:ring-blue-500"
                  >
                    {checked.models.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.label}{m.id === checked.recommended ? ' (recommended)' : ''}
                      </option>
                    ))}
                  </select>
                </div>
                <label className="flex items-center gap-2 text-sm text-gray-700">
                  <input type="checkbox" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
                  Remember on this device (otherwise it's forgotten when you close the tab)
                </label>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={!model}
                  className="px-4 py-2 rounded-lg bg-green-600 text-white text-sm font-medium hover:bg-green-700 disabled:opacity-50"
                >
                  Use this key
                </button>
              </>
            ) : (
              <p className="text-sm text-gray-600">This key can't use any chat models. Check its permissions.</p>
            )}
          </div>
        )}
      </section>

      {/* Privacy */}
      <section className="rounded-xl bg-gray-100 p-4 text-sm text-gray-600 space-y-1">
        <h2 className="font-semibold text-gray-800">Is my key safe?</h2>
        <p>Your key is kept in <strong>this browser only</strong>. It's sent with AI requests, over HTTPS, so our
          server can pass it to {providerName(provider)} for that one request — it's never saved or logged on the
          server.</p>
        <p>Good habits: create a key just for CoopRadar, set a spending limit in your provider's dashboard, and
          delete the key there when you're done.</p>
      </section>
    </div>
  )
}
