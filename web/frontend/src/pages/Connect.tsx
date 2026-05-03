import { useState, type KeyboardEvent as ReactKeyboardEvent } from 'react'
import { api, type ConnectorToken } from '../api/client'

type ClientKey = 'claude' | 'chatgpt' | 'gemini'
type CopyKey = 'mcp' | 'token' | 'oneliner'

type ClientSetup = {
  key: ClientKey
  label: string
  addServer: string
  oneLinerHint: string
  testHint: string
  troubleshooting: { issue: string; fix: string }[]
}

export const ONE_LINER =
  'When connected to Kindred, read the kindred://guide resource before doing anything else.'

const CLIENTS: ClientSetup[] = [
  {
    key: 'claude',
    label: 'Claude Projects',
    addServer:
      'In Claude.ai, open Settings → Connectors → Add custom connector. Paste the MCP URL above and your connector token.',
    oneLinerHint: 'Create a Project. In its instructions, paste:',
    testHint:
      'Open the project and say "Hi, I\'d like to journal." You should get one gentle open question, no advice.',
    troubleshooting: [
      { issue: 'Connector greyed out', fix: 'Re-mint the token above and paste it again.' },
      {
        issue: 'AI ignores the one-liner',
        fix: 'Paste the kindred://guide content directly into project instructions.',
      },
    ],
  },
  {
    key: 'chatgpt',
    label: 'ChatGPT',
    addServer:
      'Create a Custom GPT. In Configure → Actions, add the MCP URL above with the connector token as the bearer.',
    oneLinerHint: 'In Custom GPT instructions, paste:',
    testHint:
      'In the GPT, say "Hi, I\'d like to journal." Then say "Let\'s save this session" and confirm save_entry runs.',
    troubleshooting: [
      { issue: '401 unauthorized', fix: 'Token may have rotated — re-mint and update the GPT auth.' },
      {
        issue: 'Tool not invoked',
        fix: 'Add a stronger instruction, e.g. "Always call kindred tools when the user asks to save or search."',
      },
    ],
  },
  {
    key: 'gemini',
    label: 'Gemini Gems',
    addServer:
      'Create a Gem. In its custom instructions / extensions, register the MCP server above with the bearer token.',
    oneLinerHint: 'In the Gem instructions, paste:',
    testHint:
      'Open the Gem and say "Hi, I\'d like to journal." Confirm the AI asks one open question, then say "Let\'s save this session."',
    troubleshooting: [
      {
        issue: "Gem can't see the MCP server",
        fix: "Some Gemini surfaces don't support arbitrary MCP yet — use a client that does, or follow the kindred-start prompt manually.",
      },
    ],
  },
]

export function Connect() {
  const [token, setToken] = useState<ConnectorToken | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copiedKey, setCopiedKey] = useState<CopyKey | null>(null)
  const [activeClient, setActiveClient] = useState<ClientKey>('claude')

  const mint = async () => {
    setError(null)
    try {
      const next = await api.post<ConnectorToken>('/connect/token')
      setToken(next)
    } catch (e) {
      setError((e as Error).message)
    }
  }

  const copy = async (text: string, key: CopyKey) => {
    try {
      await navigator.clipboard.writeText(text)
      setCopiedKey(key)
      setTimeout(() => setCopiedKey((k) => (k === key ? null : k)), 1500)
    } catch (e) {
      setError(
        `Couldn't copy to clipboard (${(e as Error).message}). ` +
          `Select the text and copy it manually.`,
      )
    }
  }

  const copyButton = (value: string, key: CopyKey, label: string) => (
    <button
      type="button"
      className="btn btn-secondary"
      aria-label={label}
      onClick={() => void copy(value, key)}
    >
      {copiedKey === key ? 'Copied' : 'Copy'}
    </button>
  )

  const MCP_URL = import.meta.env.VITE_MCP_BASE_URL
    ? `${import.meta.env.VITE_MCP_BASE_URL}/sse`
    : 'https://kindred-mcp.interstellarai.net/sse'

  const client = CLIENTS.find((c) => c.key === activeClient)!

  const onTabKeyDown = (e: ReactKeyboardEvent<HTMLButtonElement>) => {
    if (e.key !== 'ArrowLeft' && e.key !== 'ArrowRight') return
    e.preventDefault()
    const idx = CLIENTS.findIndex((x) => x.key === activeClient)
    const next =
      e.key === 'ArrowRight'
        ? CLIENTS[(idx + 1) % CLIENTS.length]
        : CLIENTS[(idx - 1 + CLIENTS.length) % CLIENTS.length]
    setActiveClient(next.key)
    document.getElementById(`tab-${next.key}`)?.focus()
  }

  return (
    <>
      <div className="page-head">
        <div className="page-eye">
          <span className="glyph">◈</span> Connector
        </div>
        <h1 className="page-title">
          Connect Kindred to <em>your AI assistant</em>.
        </h1>
        <p className="page-sub">
          Two minutes. Paste these into your AI assistant&apos;s connector settings. Once connected,
          the three slash commands light up.
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
          {copyButton(MCP_URL, 'mcp', 'Copy MCP server URL')}
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
          {token && copyButton(token.token, 'token', 'Copy connector token')}
        </div>

        {error && (
          <p style={{ color: 'var(--rust)', fontSize: 13, margin: '0 0 var(--sp-3)' }}>
            {error}
          </p>
        )}

        {/* Step 3 — per-client tabs */}
        <div className="entry-section-eye">Step 3 · Set up your AI</div>

        <div
          role="tablist"
          aria-label="AI client"
          style={{
            display: 'flex',
            gap: 0,
            borderBottom: '1px solid var(--border)',
            marginBottom: 'var(--sp-4)',
            flexWrap: 'wrap',
          }}
        >
          {CLIENTS.map((c) => {
            const isActive = c.key === activeClient
            return (
              <button
                key={c.key}
                id={`tab-${c.key}`}
                type="button"
                role="tab"
                aria-selected={isActive}
                aria-controls={`panel-${c.key}`}
                tabIndex={isActive ? 0 : -1}
                onClick={() => setActiveClient(c.key)}
                onKeyDown={onTabKeyDown}
                style={{
                  background: isActive ? 'var(--bg-elevated)' : 'transparent',
                  border: 'none',
                  borderBottom: isActive
                    ? '2px solid var(--terracotta)'
                    : '2px solid transparent',
                  marginBottom: -1,
                  padding: '10px 16px',
                  fontFamily: 'var(--font-sans)',
                  fontSize: 14,
                  color: isActive ? 'var(--ink)' : 'var(--ink-3)',
                  cursor: 'pointer',
                  fontWeight: isActive ? 500 : 400,
                }}
              >
                {c.label}
              </button>
            )
          })}
        </div>

        <div
          role="tabpanel"
          id={`panel-${client.key}`}
          aria-labelledby={`tab-${client.key}`}
        >
          <div className="entry-section-eye">Step 1 · Add the MCP server</div>
          <p
            style={{
              color: 'var(--ink-2)',
              fontSize: 14,
              lineHeight: 1.55,
              margin: '8px 0 var(--sp-4)',
              maxWidth: '64ch',
            }}
          >
            {client.addServer}
          </p>

          <div className="entry-section-eye">Step 2 · Custom instruction</div>
          <p
            style={{
              color: 'var(--ink-2)',
              fontSize: 14,
              lineHeight: 1.55,
              margin: '8px 0 var(--sp-3)',
              maxWidth: '64ch',
            }}
          >
            {client.oneLinerHint}
          </p>
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
                wordBreak: 'break-word',
              }}
            >
              {ONE_LINER}
            </code>
            {copyButton(ONE_LINER, 'oneliner', 'Copy one-liner instruction')}
          </div>

          <div className="entry-section-eye">Step 3 · Test it</div>
          <p
            style={{
              color: 'var(--ink-2)',
              fontSize: 14,
              lineHeight: 1.55,
              margin: '8px 0 var(--sp-4)',
              maxWidth: '64ch',
            }}
          >
            {client.testHint}
          </p>

          <div className="entry-section-eye">Step 4 · Troubleshooting</div>
          <ul
            style={{
              color: 'var(--ink-2)',
              fontSize: 14,
              lineHeight: 1.55,
              margin: '8px 0 0',
              paddingLeft: 20,
              maxWidth: '64ch',
            }}
          >
            {client.troubleshooting.map((t) => (
              <li key={t.issue} style={{ marginBottom: 6 }}>
                <strong>{t.issue}</strong> — {t.fix}
              </li>
            ))}
          </ul>
        </div>
      </div>
    </>
  )
}
