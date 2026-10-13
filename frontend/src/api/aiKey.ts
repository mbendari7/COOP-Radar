/**
 * The visitor's own AI key.
 *
 * It lives only in this browser. sessionStorage by default so it is gone when the tab closes,
 * or localStorage if the visitor ticks Remember on this device.
 * It only goes along with AI requests like matching and questions, as X-AI headers. The server
 * passes it to the provider for that one request and never keeps it.
 */

import { useMutation } from '@tanstack/react-query'
import { useSyncExternalStore } from 'react'
import { apiFetch } from './client'

export type AiProvider = 'anthropic' | 'openai' | 'gemini'

export interface SavedAiKey {
  provider: AiProvider
  apiKey: string
  model: string
  remember: boolean
}

const STORAGE_KEY = 'coopradar.aiKey'
const CHANGE_EVENT = 'coopradar:ai-key-changed'

function read(): SavedAiKey | null {
  try {
    const raw = sessionStorage.getItem(STORAGE_KEY) ?? localStorage.getItem(STORAGE_KEY)
    return raw ? (JSON.parse(raw) as SavedAiKey) : null
  } catch {
    return null // storage is blocked in private mode or the value is broken
  }
}

// useSyncExternalStore needs a steady snapshot so we cache the parsed value for each raw string
let cachedRaw: string | null = null
let cachedValue: SavedAiKey | null = null
function snapshot(): SavedAiKey | null {
  let raw: string | null = null
  try {
    raw = sessionStorage.getItem(STORAGE_KEY) ?? localStorage.getItem(STORAGE_KEY)
  } catch {
    raw = null
  }
  if (raw !== cachedRaw) {
    cachedRaw = raw
    cachedValue = read()
  }
  return cachedValue
}

export function saveAiKey(key: SavedAiKey): void {
  try {
    clearStorage()
    const store = key.remember ? localStorage : sessionStorage
    store.setItem(STORAGE_KEY, JSON.stringify(key))
  } finally {
    window.dispatchEvent(new Event(CHANGE_EVENT))
  }
}

function clearStorage(): void {
  try {
    sessionStorage.removeItem(STORAGE_KEY)
    localStorage.removeItem(STORAGE_KEY)
  } catch {
    // nothing to do if storage is blocked
  }
}

export function clearAiKey(): void {
  clearStorage()
  window.dispatchEvent(new Event(CHANGE_EVENT))
}

function subscribe(onChange: () => void): () => void {
  window.addEventListener(CHANGE_EVENT, onChange)
  window.addEventListener('storage', onChange) // other tabs
  return () => {
    window.removeEventListener(CHANGE_EVENT, onChange)
    window.removeEventListener('storage', onChange)
  }
}

/** The saved key or null. Redraws whenever it changes anywhere in the app. */
export function useAiKey(): SavedAiKey | null {
  return useSyncExternalStore(subscribe, snapshot, () => null)
}

/** Headers for AI requests. Empty when no key is saved, and then the server may use its own. */
export function aiHeaders(): Record<string, string> {
  const key = read()
  return key
    ? { 'X-AI-Provider': key.provider, 'X-AI-Key': key.apiKey, 'X-AI-Model': key.model }
    : {}
}

// Checking a key with its provider

export interface AiModelOption {
  id: string
  label: string
}

export interface AiKeyCheckResult {
  provider: AiProvider
  models: AiModelOption[]
  recommended: string | null
}

export function useCheckAiKey() {
  return useMutation({
    mutationFn: (body: { provider: AiProvider; api_key: string }) =>
      apiFetch<AiKeyCheckResult>('/api/ai/check', { method: 'POST', json: body }),
  })
}

// How to get a key from each provider

export interface ProviderGuide {
  id: AiProvider
  name: string
  company: string
  keyPrefix: string
  consoleUrl: string
  steps: string[]
  cost: string
}

export const PROVIDER_GUIDES: ProviderGuide[] = [
  {
    id: 'gemini',
    name: 'Gemini',
    company: 'Google',
    keyPrefix: 'AIza…',
    consoleUrl: 'https://aistudio.google.com/apikey',
    steps: [
      'Open Google AI Studio and sign in with your Google account.',
      'Click "Get API key", then "Create API key".',
      'Copy the key (it starts with "AIza") and paste it below.',
    ],
    cost: 'Has a free tier with usage limits, so it is the easiest way to start. On the free tier Google may use your inputs to improve its products.',
  },
  {
    id: 'openai',
    name: 'ChatGPT',
    company: 'OpenAI',
    keyPrefix: 'sk-…',
    consoleUrl: 'https://platform.openai.com/api-keys',
    steps: [
      'Sign in at platform.openai.com (this is separate from a ChatGPT Plus subscription).',
      'Add credit under Settings, then Billing. The API is pay-as-you-go.',
      'Go to API keys → "Create new secret key", copy it, and paste it below.',
    ],
    cost: 'Pay per use from prepaid credit. A resume match plus a few questions usually costs cents.',
  },
  {
    id: 'anthropic',
    name: 'Claude',
    company: 'Anthropic',
    keyPrefix: 'sk-ant-…',
    consoleUrl: 'https://console.anthropic.com/settings/keys',
    steps: [
      'Sign in at console.anthropic.com (separate from a Claude.ai subscription).',
      'Add credit under Settings, then Billing. The API is pay-as-you-go.',
      'Go to API keys → "Create Key", copy it, and paste it below.',
    ],
    cost: 'Pay per use from prepaid credit. A resume match plus a few questions usually costs cents.',
  },
]

export function providerName(provider: AiProvider): string {
  return PROVIDER_GUIDES.find((g) => g.id === provider)?.name ?? provider
}
