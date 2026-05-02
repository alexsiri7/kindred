import { useEffect, useRef, useState } from 'react'
import { supabase } from '../lib/supabase'

const MCP_BASE = import.meta.env.VITE_MCP_BASE_URL ?? 'https://kindred-mcp.interstellarai.net'

export function McpAuth() {
  const [status, setStatus] = useState<'starting' | 'completing' | 'error'>('starting')
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
      setErrorMsg('No OAuth session in progress. Please restart the connection from Claude.')
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

  if (status === 'error') {
    return (
      <div className="flex min-h-screen items-center justify-center bg-stone-50">
        <div className="w-full max-w-sm rounded-lg border border-red-200 bg-white p-8 text-center shadow-sm">
          <h2 className="text-lg font-semibold text-red-700">Connection failed</h2>
          <p className="mt-2 text-sm text-stone-600">{errorMsg}</p>
        </div>
      </div>
    )
  }

  return (
    <div className="flex min-h-screen items-center justify-center bg-stone-50">
      <div className="text-center text-stone-600">
        {status === 'completing' ? 'Completing authentication…' : 'Connecting to Claude…'}
      </div>
    </div>
  )
}
