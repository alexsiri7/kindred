import { Navigate } from 'react-router'
import { supabase } from '../lib/supabase'
import { useAuth } from '../store/auth'

export function Login() {
  const session = useAuth((s) => s.session)
  if (session) return <Navigate to="/" replace />

  const signIn = () => {
    void supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin + '/' },
    })
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-stone-50">
      <div className="w-full max-w-sm space-y-6 rounded-lg border border-stone-200 bg-white p-8 text-center shadow-sm">
        <div>
          <h1 className="text-2xl font-semibold">Kindred</h1>
          <p className="mt-2 text-sm text-stone-600">
            A reflective journaling companion.
          </p>
        </div>
        <button
          type="button"
          onClick={signIn}
          className="w-full rounded bg-stone-900 px-4 py-2 text-white hover:bg-stone-800"
        >
          Sign in with Google
        </button>
      </div>
    </div>
  )
}
