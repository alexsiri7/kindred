import { useState } from 'react'
import { api, type ConnectorToken } from '../api/client'

export function Connect() {
  const [token, setToken] = useState<ConnectorToken | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)

  const mint = async () => {
    setError(null)
    try {
      const next = await api.post<ConnectorToken>('/connect/token')
      setToken(next)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const copy = async () => {
    if (!token) return
    await navigator.clipboard.writeText(token.token)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  return (
    <div className="space-y-6">
      <h1 className="text-2xl font-semibold">Connect to Claude.ai</h1>
      <p className="text-sm text-stone-700">
        Mint a connector token below and paste it into the Kindred connector
        config in Claude.ai. Existing tokens stay valid.
      </p>
      <button
        type="button"
        onClick={() => void mint()}
        className="rounded bg-stone-900 px-4 py-2 text-white hover:bg-stone-800"
      >
        Mint new token
      </button>
      {error && <p className="text-red-700">{error}</p>}
      {token && (
        <div className="rounded border border-stone-200 bg-white p-4">
          <div className="text-xs text-stone-500">Your new token:</div>
          <code className="mt-2 block break-all rounded bg-stone-100 p-3 text-sm">
            {token.token}
          </code>
          <button
            type="button"
            onClick={() => void copy()}
            className="mt-3 rounded border border-stone-300 px-3 py-1 text-sm hover:bg-stone-100"
          >
            {copied ? 'Copied' : 'Copy'}
          </button>
        </div>
      )}
    </div>
  )
}
