import { useState } from 'react'
import { api, type ConnectorToken } from '../api/client'

type ClientKey = 'claude-desktop' | 'cursor' | 'windsurf'

type ClientSetup = {
  key: ClientKey
  label: string
  addServer: string
  oneLinerHint: string
  testHint: string
  troubleshooting: { issue: string; fix: string }[]
  docsUrl: string
}

export const ONE_LINER =
  'When connected to Kindred, call the read_guide tool before doing anything else.'

const CLIENTS: ClientSetup[] = [
  {
    key: 'claude-desktop',
    label: 'Claude Desktop',
    addServer:
      'Open claude_desktop_config.json (macOS: ~/Library/Application Support/Claude/claude_desktop_config.json, Windows: %APPDATA%\\Claude\\claude_desktop_config.json). Under "mcpServers", add an entry with "command": "npx", "args": ["mcp-remote@latest", "<MCP URL>", "--header", "Authorization: Bearer <token>"]. Save the file and fully quit and relaunch Claude Desktop.',
    oneLinerHint: 'Create a new Project. In its system prompt / instructions, paste:',
    testHint:
      'Open the project and say "Hi, I\'d like to journal." You should see the read_guide tool called automatically, then one gentle open question with no advice.',
    troubleshooting: [
      {
        issue: 'Server not listed in Claude',
        fix: 'Fully quit Claude Desktop (Cmd+Q / Alt+F4) and relaunch — the config is only read at startup.',
      },
      {
        issue: '401 Unauthorized',
        fix: 'Re-mint your connector token above and update the Authorization header value in the config, then restart.',
      },
      {
        issue: 'npx not found',
        fix: 'Ensure Node.js 18+ is installed. Run "npx mcp-remote@latest --version" in a terminal to verify.',
      },
    ],
    docsUrl: 'https://modelcontextprotocol.io/docs/develop/connect-local-servers',
  },
  {
    key: 'cursor',
    label: 'Cursor',
    addServer:
      'Create or open ~/.cursor/mcp.json (global) or .cursor/mcp.json in your project root. Add an entry under "mcpServers" with "url": "<MCP URL>" and "headers": {"Authorization": "Bearer <token>"}. Save the file — Cursor picks up the change immediately without a restart.',
    oneLinerHint: 'In Cursor Rules (global or per-project), paste:',
    testHint:
      'Open a Cursor chat and say "Hi, I\'d like to journal." The read_guide tool should be called first, then you\'ll get one gentle question.',
    troubleshooting: [
      {
        issue: 'Server not appearing in Cursor',
        fix: 'Check that your mcp.json is valid JSON. Open Settings → MCP to see the server list and any error messages.',
      },
      {
        issue: '401 Unauthorized',
        fix: 'Re-mint your connector token above and update the Authorization header value in mcp.json.',
      },
      {
        issue: 'Tools not invoked',
        fix: 'Make sure Agent mode is enabled (not plain Chat). MCP tools are only available in Agent mode.',
      },
    ],
    docsUrl: 'https://cursor.com/docs/mcp',
  },
  {
    key: 'windsurf',
    label: 'Windsurf',
    addServer:
      'Open ~/.codeium/windsurf/mcp_config.json. Add an entry under "mcpServers" with "serverUrl": "<MCP URL>" and "headers": {"Authorization": "Bearer <token>"}. Save the file and reload Windsurf (Cmd+Shift+P → "Reload Window").',
    oneLinerHint: 'In Windsurf global rules or your workspace instructions, paste:',
    testHint:
      'Open the Cascade panel and say "Hi, I\'d like to journal." The read_guide tool should fire first, then you\'ll get one open question.',
    troubleshooting: [
      {
        issue: 'Server not listed in Cascade',
        fix: 'Reload the window (Cmd+Shift+P → "Reload Window") after editing mcp_config.json. Check the Cascade panel for error details.',
      },
      {
        issue: '401 Unauthorized',
        fix: 'Re-mint your connector token above and update the Authorization header value in mcp_config.json.',
      },
      {
        issue: 'mcp_config.json not found',
        fix: 'Create the file and its parent directory: mkdir -p ~/.codeium/windsurf && echo \'{"mcpServers":{}}\' > ~/.codeium/windsurf/mcp_config.json',
      },
    ],
    docsUrl: 'https://docs.windsurf.com/windsurf/cascade/mcp',
  },
]

export function Connect() {
  const [token, setToken] = useState<ConnectorToken | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [copied, setCopied] = useState(false)
  const [activeClient, setActiveClient] = useState<ClientKey>('claude-desktop')

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
    ? `${import.meta.env.VITE_MCP_BASE_URL}/mcp`
    : 'https://kindred-mcp.interstellarai.net/mcp'

  const client = CLIENTS.find((c) => c.key === activeClient) ?? CLIENTS[0]

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
          role="note"
          style={{
            background: 'var(--paper-2)',
            border: '1px solid var(--rust-2, var(--rust))',
            borderLeftWidth: 3,
            borderRadius: 'var(--r-md)',
            padding: '10px 14px',
            marginBottom: 'var(--sp-3)',
            fontSize: 13,
            color: 'var(--ink-2)',
            lineHeight: 1.5,
          }}
        >
          <strong>Treat this token like a password.</strong> Anyone who has it
          can read your journal. Don&apos;t paste it into chat, screenshots, or
          shared docs.
        </div>
        <div
          style={{
            display: 'flex',
            gap: 8,
            alignItems: 'center',
            marginBottom: token?.expires_at ? 4 : 'var(--sp-4)',
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

        {token?.expires_at && (
          <p
            style={{
              fontSize: 12,
              color: 'var(--ink-3)',
              margin: '0 0 var(--sp-4)',
            }}
          >
            Expires {new Date(token.expires_at).toLocaleDateString()}
          </p>
        )}

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
                type="button"
                role="tab"
                aria-selected={isActive}
                onClick={() => setActiveClient(c.key)}
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

        <div role="tabpanel" aria-label={`${client.label} setup`}>
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
            <button
              type="button"
              className="btn btn-secondary"
              onClick={() => void copy(ONE_LINER)}
            >
              Copy
            </button>
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
          <a
            href={client.docsUrl}
            target="_blank"
            rel="noopener noreferrer"
            style={{ color: 'var(--terracotta)', fontSize: 14, display: 'inline-block', marginTop: 'var(--sp-3)' }}
          >
            Official docs →
          </a>
        </div>
      </div>
    </>
  )
}
