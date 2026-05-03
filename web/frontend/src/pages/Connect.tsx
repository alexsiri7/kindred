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

  const copy = async (text: string) => {
    await navigator.clipboard.writeText(text)
    setCopied(true)
    setTimeout(() => setCopied(false), 1500)
  }

  const MCP_URL = import.meta.env.VITE_MCP_BASE_URL
    ? `${import.meta.env.VITE_MCP_BASE_URL}/sse`
    : 'https://kindred-mcp.interstellarai.net/sse'

  return (
    <>
      <div className="page-head">
        <div className="page-eye">
          <span className="glyph">◈</span> Connector
        </div>
        <h1 className="page-title">
          Add Kindred to <em>Claude</em>.
        </h1>
        <p className="page-sub">
          Two minutes. Paste this into Claude.ai&apos;s connector settings. Once connected, the
          three slash commands light up.
        </p>
      </div>

      <div
        style={{
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--r-lg)',
          padding: 'var(--sp-5)',
          marginBottom: 'var(--sp-5)',
        }}
      >
        {/* Step 1 */}
        <div className="entry-section-eye">Step 1 · MCP server URL</div>
        <div
          style={{
            display: 'flex',
            gap: 8,
            alignItems: 'center',
            marginBottom: 'var(--sp-4)',
          }}
        >
          <code
            style={{
              flex: 1,
              padding: '12px 14px',
              background: 'var(--paper-2)',
              border: '1px solid var(--border)',
              borderRadius: 'var(--r-md)',
              fontFamily: 'var(--font-mono)',
              fontSize: 13,
              color: 'var(--ink)',
              wordBreak: 'break-all',
            }}
          >
            {MCP_URL}
          </code>
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => void copy(MCP_URL)}
          >
            Copy
          </button>
        </div>

        {/* Step 2 */}
        <div className="entry-section-eye">Step 2 · Connector token</div>
        <div
          style={{
            display: 'flex',
            gap: 8,
            alignItems: 'center',
            marginBottom: 'var(--sp-4)',
          }}
        >
          {token ? (
            <code
              style={{
                flex: 1,
                padding: '12px 14px',
                background: 'var(--paper-2)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--r-md)',
                fontFamily: 'var(--font-mono)',
                fontSize: 13,
                color: 'var(--ink)',
                wordBreak: 'break-all',
              }}
            >
              {token.token}
            </code>
          ) : (
            <code
              style={{
                flex: 1,
                padding: '12px 14px',
                background: 'var(--paper-2)',
                border: '1px solid var(--border)',
                borderRadius: 'var(--r-md)',
                fontFamily: 'var(--font-mono)',
                fontSize: 13,
                color: 'var(--ink-3)',
              }}
            >
              kdr_••••••••••••••••••••••••
            </code>
          )}
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => void mint()}
          >
            {token ? 'Rotate' : 'Mint token'}
          </button>
          {token && (
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => void copy(token.token)}
            >
              {copied ? 'Copied' : 'Copy'}
            </button>
          )}
        </div>

        {error && (
          <p style={{ color: 'var(--rust)', fontSize: 13, margin: '0 0 var(--sp-3)' }}>
            {error}
          </p>
        )}

        {/* Step 3 */}
        <div className="entry-section-eye">Step 3 · Try it</div>
        <p
          style={{
            color: 'var(--ink-2)',
            fontSize: 14,
            lineHeight: 1.55,
            margin: '8px 0 0',
            maxWidth: '56ch',
          }}
        >
          In Claude.ai, type{' '}
          <code>/kindred-start</code> to begin a session. That&apos;s it.
        </p>
      </div>
    </>
  )
}
