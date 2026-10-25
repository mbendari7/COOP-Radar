/**
 * The sign in page at /sign-in. ?tab=register opens on making an account and ?next=/path
 * says where to go back to after, like the jobs list someone was saving from.
 */

import { useNavigate, useSearchParams } from 'react-router-dom'
import AuthForm from '../components/AuthForm'

/** Only paths on this site, so a link can't send people somewhere else after signing in. */
function safeNext(raw: string | null): string {
  return raw && raw.startsWith('/') && !raw.startsWith('//') ? raw : '/'
}

export default function SignInPage() {
  const [sp] = useSearchParams()
  const navigate = useNavigate()
  const next = safeNext(sp.get('next'))
  const tab = sp.get('tab') === 'register' ? 'register' : 'login'

  return (
    <div className="mx-auto max-w-md px-4 py-10 sm:py-14">
      <h1 className="display text-[26px] leading-tight text-gray-900">
        {tab === 'register' ? 'Create your account' : 'Sign in'}
      </h1>
      <p className="mt-2 text-[15px] text-gray-700">
        Save jobs, track your applications and keep your resume matches.
      </p>
      <div className="mt-6">
        <AuthForm initialTab={tab} autoFocus onDone={() => navigate(next, { replace: true })} />
      </div>
    </div>
  )
}
