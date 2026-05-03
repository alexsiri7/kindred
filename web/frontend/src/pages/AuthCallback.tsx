import { useEffect, useRef, useState } from 'react'
import { Navigate } from 'react-router'
import { supabase } from '../lib/supabase'

type Status = 'exchanging' | 'success' | 'error'

export function AuthCallback() {
  const [status, setStatus] = useState<Status>('exchanging')
  const [errorMsg, setErrorMsg] = useState('')
  const ran = useRef(false)

  useEffect(() => {
    // React StrictMode runs effects twice in dev — and PKCE codes are
    // single-use, so the second exchange would fail. Mirror McpAuth.tsx.
    if (ran.current) return
    ran.current = true

    const params = new URLSearchParams(window.location.search)
    const code = params.get('code')
    const errParam = params.get('error_description') ?? params.get('error')

    if (errParam) {
      setStatus('error')
      setErrorMsg(errParam)
      return
    }
    if (!code) {
      setStatus('error')
      setErrorMsg('Missing authorization code.')
      return
    }

    void supabase.auth.exchangeCodeForSession(code).then(({ error }) => {
      if (error) {
        setStatus('error')
        setErrorMsg(error.message)
      } else {
        setStatus('success')
      }
    })
  }, [])

  if (status === 'success') return <Navigate to="/app" replace />
  if (status === 'error') {
    const qs = new URLSearchParams({ error: errorMsg }).toString()
    return <Navigate to={`/login?${qs}`} replace />
  }

  return (
    <div
      style={{
        minHeight: '100vh',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        background: 'var(--paper)',
        color: 'var(--ink-3)',
        fontFamily: 'var(--font-mono)',
        fontSize: 12,
        letterSpacing: '0.08em',
        textTransform: 'uppercase',
      }}
    >
      Signing in…
    </div>
  )
}
