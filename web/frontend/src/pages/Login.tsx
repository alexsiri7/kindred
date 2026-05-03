import { Navigate, useSearchParams } from 'react-router'
import { supabase } from '../lib/supabase'
import { useAuth } from '../store/auth'
import { KindredMark } from '../components/Brand'
import { Button } from '../components/Button'

export function Login() {
  const session = useAuth((s) => s.session)
  const [searchParams] = useSearchParams()
  const errorMsg = searchParams.get('error')
  if (session) return <Navigate to="/app" replace />

  const signIn = () => {
    void supabase.auth.signInWithOAuth({
      provider: 'google',
      options: { redirectTo: window.location.origin + '/auth/callback' },
    })
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--paper)',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 380,
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--r-xl)',
          padding: 'var(--sp-7)',
          boxShadow: 'var(--shadow-md)',
          textAlign: 'center',
        }}
      >
        <div
          style={{
            display: 'flex',
            alignItems: 'center',
            justifyContent: 'center',
            gap: 10,
            marginBottom: 'var(--sp-6)',
          }}
        >
          <KindredMark size={36} />
          <span
            style={{
              fontFamily: 'var(--font-display)',
              fontSize: 28,
              lineHeight: 1,
              letterSpacing: '-0.01em',
            }}
          >
            <em>Kindred</em>
            <span style={{ color: 'var(--terracotta)' }}>.</span>
          </span>
        </div>

        <h1
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: 'var(--fs-h3)',
            fontWeight: 400,
            margin: '0 0 var(--sp-2)',
          }}
        >
          Sign in to your <em>journal</em>
        </h1>
        <p
          style={{
            color: 'var(--ink-3)',
            fontSize: 'var(--fs-sm)',
            marginBottom: 'var(--sp-6)',
          }}
        >
          A reflective journaling companion.
        </p>

        {errorMsg && (
          <p
            style={{
              color: 'var(--rust)',
              fontSize: 'var(--fs-sm)',
              marginBottom: 'var(--sp-4)',
            }}
            role="alert"
          >
            {errorMsg}
          </p>
        )}

        <Button
          variant="primary"
          size="lg"
          onClick={signIn}
          style={{ width: '100%', justifyContent: 'center' }}
        >
          Sign in with Google
        </Button>
      </div>
    </div>
  )
}
