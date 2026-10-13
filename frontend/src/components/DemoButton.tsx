/**
 * One click to look around CoopRadar with a private demo account that already has sample data.
 * Shows nothing when the server has demo accounts turned off.
 */

import { useNavigate } from 'react-router-dom'
import { useDemoLogin } from '../api/auth'
import { usePublicConfig } from '../api/meta'

interface Props {
  /** primary is the red button, secondary the outlined one, header sits on the red bar */
  variant?: 'primary' | 'secondary' | 'header'
  label?: string
}

export default function DemoButton({ variant = 'primary', label = 'Try the demo' }: Props) {
  const { data: config } = usePublicConfig()
  const demo = useDemoLogin()
  const navigate = useNavigate()

  if (!config?.demo_enabled) return null

  const className = {
    header: 'rounded-sm border-2 border-white/80 px-3 py-1 text-sm font-bold text-white hover:border-white hover:bg-white/10 whitespace-nowrap',
    primary: 'btn-primary',
    secondary: 'btn-secondary',
  }[variant]

  return (
    <span className="inline-flex flex-col items-start">
      <button
        type="button"
        onClick={() => demo.mutate(undefined, { onSuccess: () => navigate('/resume') })}
        disabled={demo.isPending}
        className={`${className} disabled:opacity-60`}
      >
        {demo.isPending ? 'Setting up the sample...' : label}
      </button>
      {demo.isError && (
        <span role="alert" className={`mt-1 text-xs ${variant === 'header' ? 'text-white' : 'text-post-700'}`}>
          {demo.error.message || 'Could not start the demo.'}
        </span>
      )}
    </span>
  )
}
