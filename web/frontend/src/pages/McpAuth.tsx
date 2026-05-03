import { useEffect, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'
import { KindredWordmark } from '../components/Brand'

const MCP_BASE = import.meta.env.VITE_MCP_BASE_URL ?? 'https://kindred-mcp.interstellarai.net'

export function McpAuth() {
  const [status, setStatus] = useState<'starting' | 'completing' | 'done' | 'error'>('starting')
  const [errorMsg, setErrorMsg] = useState('')
  const ran = useRef(false)

  useEffect(() => {
    if (ran.current) return
    ran.current = true

    const params = new URLSearchParams(window.location.search)
    const flowId = params.get('flow')

    if (flowId) {
      sessionStorage.setItem('mcp_flow_id', flowId)
      void supabase.auth.signInWithOAuth({
        provider: 'google',
        options: { redirectTo: `${window.location.origin}/mcp-auth` },
      })
      return
    }

    const storedFlowId = sessionStorage.getItem('mcp_flow_id')
    if (!storedFlowId) {
      setStatus('error')
      setErrorMsg('No OAuth session in progress. Please restart the connection from your MCP client.')
      return
    }

    setStatus('completing')

    let completing = false
    async function completeFlow(accessToken: string) {
      if (completing) return
      completing = true
      try {
        const resp = await fetch(`${MCP_BASE}/oauth/code-from-session`, {
          method: 'POST',
          headers: { 'Content-Type': 'application/json' },
          body: JSON.stringify({ flow_id: storedFlowId, access_token: accessToken }),
        })
        if (!resp.ok) {
          const text = await resp.text()
          throw new Error(`Server error ${resp.status}: ${text}`)
        }
        const { redirect_url } = (await resp.json()) as { redirect_url: string }
        sessionStorage.removeItem('mcp_flow_id')
        setStatus('done')
        window.location.href = redirect_url
      } catch (err) {
        setStatus('error')
        setErrorMsg(String(err))
      }
    }

    const {
      data: { subscription },
    } = supabase.auth.onAuthStateChange((_event, session) => {
      if (session) {
        subscription.unsubscribe()
        void completeFlow(session.access_token)
      }
    })

    void supabase.auth.getSession().then(({ data }) => {
      if (data.session) {
        subscription.unsubscribe()
        void completeFlow(data.session.access_token)
      }
    })

    return () => subscription.unsubscribe()
  }, [])

  const cardStyle: React.CSSProperties = {
    width: '100%',
    maxWidth: 380,
    background: 'var(--bg-elevated)',
    border: '1px solid var(--border)',
    borderRadius: 'var(--r-xl)',
    padding: 'var(--sp-7)',
    boxShadow: 'var(--shadow-md)',
    textAlign: 'center',
  }

  const wrapStyle: React.CSSProperties = {
    minHeight: '100vh',
    display: 'flex',
    alignItems: 'center',
    justifyContent: 'center',
    background: 'var(--paper)',
  }

  const brandRow = (
    <div style={{ display: 'flex', justifyContent: 'center', marginBottom: 'var(--sp-5)' }}>
      <KindredWordmark markSize={32} />
    </div>
  )

  if (status === 'error') {
    return (
      <div style={wrapStyle}>
        <div style={{ ...cardStyle, borderColor: 'var(--rust)', borderLeftWidth: 3 }}>
          {brandRow}
          <h2
            style={{
              fontFamily: 'var(--font-display)',
              fontWeight: 400,
              fontSize: 'var(--fs-h3)',
              color: 'var(--rust)',
              margin: '0 0 var(--sp-3)',
            }}
          >
            Connection failed
          </h2>
          <p style={{ color: 'var(--ink-3)', fontSize: 'var(--fs-sm)', margin: 0 }}>
            {errorMsg}
          </p>
        </div>
      </div>
    )
  }

  return (
    <div style={wrapStyle}>
      <div style={cardStyle}>
        {brandRow}
        <p
          style={{
            fontFamily: 'var(--font-mono)',
            fontSize: 12,
            color: 'var(--ink-3)',
            letterSpacing: '0.08em',
            textTransform: 'uppercase',
            margin: '0 0 var(--sp-3)',
          }}
        >
          {status === 'completing' ? 'Completing authentication…' : 'Connecting…'}
        </p>
        <div
          style={{
            display: 'inline-flex',
            gap: 6,
            alignItems: 'center',
          }}
        >
          {[0, 0.18, 0.36].map((delay, i) => (
            <span
              key={i}
              style={{
                width: 8,
                height: 8,
                borderRadius: '50%',
                background: 'var(--moss)',
                animation: `bounce 1.4s ease-in-out ${delay}s infinite`,
              }}
            />
          ))}
        </div>
      </div>
    </div>
  )
}
