/**
 * DemoButton — one click to explore CoopRadar with a private, pre-filled demo account.
 * Renders nothing when the server has demo accounts turned off.
 */

import { useNavigate } from 'react-router-dom'
import { useDemoLogin } from '../api/auth'
import { usePublicConfig } from '../api/meta'

interface Props {
  /** 'primary' = big blue call-to-action, 'hero' = white on dark backgrounds, 'header' = compact */
  variant?: 'primary' | 'hero' | 'hero-outline' | 'header'
  label?: string
}

export default function DemoButton({ variant = 'primary', label = 'Try the demo' }: Props) {
  const { data: config } = usePublicConfig()
  const demo = useDemoLogin()
  const navigate = useNavigate()

  if (!config?.demo_enabled) return null

  const className = {
    header:
      'text-sm font-medium px-3 py-1.5 rounded-lg border border-blue-600 text-blue-700 hover:bg-blue-50 whitespace-nowrap',
    primary: 'px-5 py-2.5 rounded-lg bg-blue-600 text-white font-semibold hover:bg-blue-700 shadow-sm',
    hero: 'px-5 py-2.5 rounded-lg bg-white text-blue-700 font-semibold hover:bg-blue-50 shadow-sm',
    'hero-outline': 'px-5 py-3 rounded-lg bg-white/10 text-white font-semibold ring-1 ring-white/40 hover:bg-white/20',
  }[variant]

  return (
    <span className="inline-flex flex-col items-start">
      <button
        type="button"
        onClick={() => demo.mutate(undefined, { onSuccess: () => navigate('/resume') })}
        disabled={demo.isPending}
        className={`${className} focus:outline-none focus:ring-2 focus:ring-blue-500 focus:ring-offset-2 disabled:opacity-60`}
      >
        {demo.isPending ? 'Setting up your demo…' : label}
      </button>
      {demo.isError && (
        <span role="alert" className={`mt-1 text-xs ${variant.startsWith('hero') ? 'text-red-100' : 'text-red-600'}`}>
          {demo.error.message || 'Could not start the demo.'}
        </span>
      )}
    </span>
  )
}
