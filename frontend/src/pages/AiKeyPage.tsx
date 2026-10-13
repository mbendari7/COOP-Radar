/**
 * The AI key page at /ai-key.
 *
 * Visitors bring their own Claude, ChatGPT or Gemini key
 *   1. pick a provider and follow the short steps to get a key
 *   2. paste the key and press Check key. The server asks the provider which models it can use
 *   3. pick a model and save. The key stays in this browser only
 */

import { useState } from 'react'
import { Link } from 'react-router-dom'
import { ExternalIcon } from '../components/Icons'
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
    <div className="mx-auto max-w-3xl space-y-10 px-4 py-8 sm:py-10">
      <header>
        <h1 className="display text-4xl text-gray-900 sm:text-5xl">Your AI key</h1>
        <p className="mt-3 max-w-[65ch] text-[17px] text-gray-700">
          The free features need no key. That covers skills found, popular skills and skill based job
          matches. The AI extras run on <strong>your own</strong> AI account, like a full resume review,
          smarter ranking, tailoring tips and cover letter openers. Gemini has a free tier. Pick a provider,
          get a key in a couple of minutes and paste it here.
        </p>
        {config?.server_ai_enabled && (
          <p className="mt-2 text-sm text-gray-600">
            This site also has a shared key (limited to {config.ai_daily_limit || 'unlimited'} AI actions a
            day per person), so adding your own is optional.
          </p>
        )}
      </header>

      {/* The key in use now */}
      {saved && (
        <section className="flex flex-wrap items-center justify-between gap-3 bg-air-700 p-4 text-white">
          <div>
            <p className="text-sm font-bold">
              Using your {providerName(saved.provider)} key ({mask(saved.apiKey)})
            </p>
            <p className="text-sm text-air-100">
              Model <code>{saved.model}</code> · {saved.remember ? 'remembered on this device' : 'until you close this tab'}
            </p>
            {justSaved && (
              <p className="mt-1 text-sm text-air-50">
                Saved. Go to <Link to="/resume" className="font-bold underline">Match my resume</Link> for your AI
                review, smarter job ranking and one click tailoring.
              </p>
            )}
          </div>
          <button
            type="button"
            onClick={() => { clearAiKey(); setJustSaved(false) }}
            className="rounded-sm border-2 border-white px-3 py-1.5 text-sm font-bold text-white hover:bg-white hover:text-air-800"
          >
            Remove key
          </button>
        </section>
      )}

      {/* Step 1. Pick a provider */}
      <section aria-labelledby="step1" className="border-t-[1.5px] border-gray-900 pt-4">
        <h2 id="step1" className="display text-2xl text-gray-900"><StepNumber n={1} />Choose your AI</h2>
        <div className="mt-4 grid border-[1.5px] border-gray-900 sm:grid-cols-3" role="radiogroup" aria-label="AI provider">
          {PROVIDER_GUIDES.map((g) => (
            <button
              key={g.id}
              type="button"
              role="radio"
              aria-checked={provider === g.id}
              onClick={() => chooseProvider(g.id)}
              className={`border-gray-900 p-4 text-left transition-colors [&:not(:first-child)]:border-t-[1.5px] sm:[&:not(:first-child)]:border-l-[1.5px] sm:[&:not(:first-child)]:border-t-0 ${
                provider === g.id ? 'bg-air-700 text-white' : 'bg-white text-gray-900 hover:bg-gray-100'
              }`}
            >
              <span className="block text-lg font-extrabold">{g.name}</span>
              <span className={`block text-sm ${provider === g.id ? 'text-air-100' : 'text-gray-600'}`}>by {g.company}</span>
            </button>
          ))}
        </div>
      </section>

      {/* Step 2. How to get a key */}
      <section aria-labelledby="step2" className="border-t-[1.5px] border-gray-900 pt-4">
        <h2 id="step2" className="display text-2xl text-gray-900"><StepNumber n={2} />Get a {guide.name} API key</h2>
        <ol className="mt-3 list-decimal space-y-1 pl-5 text-gray-800 marker:font-bold marker:text-post-600">
          {guide.steps.map((step) => <li key={step}>{step}</li>)}
        </ol>
        <a
          href={guide.consoleUrl}
          target="_blank"
          rel="noopener noreferrer"
          className="link mt-3 inline-flex items-center gap-1 text-sm"
        >
          Open the {guide.company} key page <ExternalIcon className="h-3.5 w-3.5" />
        </a>
        <p className="mt-3 text-sm text-gray-700"><strong>Cost</strong> {guide.cost}</p>
      </section>

      {/* Step 3. Paste it and check it */}
      <section aria-labelledby="step3" className="border-t-[1.5px] border-gray-900 pt-4">
        <h2 id="step3" className="display text-2xl text-gray-900"><StepNumber n={3} />Paste it and check it</h2>
        <form onSubmit={handleCheck} className="mt-4 flex flex-col gap-2 sm:flex-row">
          <label htmlFor="ai-key" className="sr-only">{guide.name} API key</label>
          <input
            id="ai-key"
            type="password"
            autoComplete="off"
            spellCheck={false}
            placeholder={`Paste your ${guide.name} key (${guide.keyPrefix})`}
            value={apiKey}
            onChange={(e) => { setApiKey(e.target.value); setChecked(null) }}
            className="field flex-1 py-2.5"
          />
          <button
            type="submit"
            disabled={apiKey.trim().length < 8 || check.isPending}
            className="btn-primary"
          >
            {check.isPending ? 'Checking...' : 'Check key'}
          </button>
        </form>
        {check.isError && (
          <p role="alert" className="mt-2 text-sm font-semibold text-post-700">{check.error.message}</p>
        )}

        {checked && (
          <div className="mt-4 space-y-3 border-[1.5px] border-air-700 bg-air-50 p-4">
            <p className="text-sm font-bold text-air-800">
              Key works. {checked.models.length} model{checked.models.length === 1 ? '' : 's'} available.
            </p>
            {checked.models.length > 0 ? (
              <>
                <div>
                  <label htmlFor="ai-model" className="label-form mb-1 block !text-gray-900">
                    Model <span className="font-normal normal-case tracking-normal text-gray-600">we picked a good default</span>
                  </label>
                  <select
                    id="ai-model"
                    value={model}
                    onChange={(e) => setModel(e.target.value)}
                    className="field"
                  >
                    {checked.models.map((m) => (
                      <option key={m.id} value={m.id}>
                        {m.label}{m.id === checked.recommended ? ' (recommended)' : ''}
                      </option>
                    ))}
                  </select>
                </div>
                <label className="flex items-center gap-2 text-sm text-gray-800">
                  <input type="checkbox" className="h-4 w-4" checked={remember} onChange={(e) => setRemember(e.target.checked)} />
                  Remember on this device. Otherwise it is forgotten when you close the tab
                </label>
                <button
                  type="button"
                  onClick={handleSave}
                  disabled={!model}
                  className="btn-primary"
                >
                  Use this key
                </button>
              </>
            ) : (
              <p className="text-sm text-gray-700">This key can't use any chat models. Check its permissions.</p>
            )}
          </div>
        )}
      </section>

      {/* Privacy */}
      <section className="space-y-1.5 bg-gray-100 p-5 text-sm text-gray-800">
        <h2 className="label-form !text-gray-900">Is my key safe?</h2>
        <p>Your key is kept in <strong>this browser only</strong>. It goes along with AI requests over HTTPS so our
          server can pass it to {providerName(provider)} for that one request. It is never saved or logged on the
          server.</p>
        <p>Good habits. Make a key just for CoopRadar, set a spending limit in your provider's dashboard and
          delete the key there when you're done.</p>
      </section>
    </div>
  )
}

/** The number in front of each step, in a small red square */
function StepNumber({ n }: { n: number }) {
  return (
    <span className="stretch-condensed mr-3 inline-flex h-8 w-8 -translate-y-0.5 items-center justify-center bg-post-600 align-middle text-base font-extrabold text-white" aria-hidden="true">
      {n}
    </span>
  )
}
