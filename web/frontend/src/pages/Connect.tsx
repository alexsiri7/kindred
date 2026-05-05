import { useState } from 'react'
import { api, type ConnectorToken } from '../api/client'
import { Button } from '../components/Button'

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

  const cmdRowStyle: React.CSSProperties = {
    display: 'flex',
    gap: 8,
    alignItems: 'center',
    marginTop: 'var(--sp-4)',
    flexWrap: 'wrap',
  }
  const cmdCodeStyle: React.CSSProperties = {
    flex: 1,
    minWidth: 0,
    marginTop: 0,
    padding: '12px 14px',
    fontSize: 13,
    color: 'var(--ink)',
    wordBreak: 'break-all',
  }

  return (
    <>
      <div className="page-head">
        <div className="page-eye">
          <span className="glyph">◈</span> Account
        </div>
        <h1 className="page-title">
          Connect to <em>Claude</em>
        </h1>
        <p className="page-sub">
          Two minutes to wire Kindred into Claude (or Cursor / Windsurf — pick a tab below). Once
          connected, the three slash commands light up.
        </p>
      </div>

      <ol
        className="steps steps-stack"
        style={{ listStyle: 'none', paddingLeft: 0, margin: 0 }}
      >
        {/* Step 1 — MCP URL */}
        <li className="step">
          <div className="step-num">
            <span>Step 01</span>
            <span className="glyph">✶</span>
          </div>
          <h3>
            Add the <em>MCP URL</em>
          </h3>
          <p>This is the server your AI assistant will talk to.</p>
          <div style={cmdRowStyle}>
            <code className="step-cmd" style={cmdCodeStyle}>
              {MCP_URL}
            </code>
            <Button variant="secondary" onClick={() => void copy(MCP_URL)}>
              Copy
            </Button>
          </div>
        </li>

        {/* Step 2 — Connector token */}
        <li className="step">
          <div className="step-num">
            <span>Step 02</span>
            <span className="glyph">✶</span>
          </div>
          <h3>
            Mint a <em>connector token</em>
          </h3>
          <p>Mint once, paste into your AI assistant&apos;s connector settings.</p>
          <div
            role="note"
            style={{
              background: 'var(--paper-2)',
              border: '1px solid var(--rust-2, var(--rust))',
              borderLeftWidth: 3,
              borderRadius: 'var(--r-md)',
              padding: '10px 14px',
              marginTop: 'var(--sp-3)',
              fontSize: 13,
              color: 'var(--ink-2)',
              lineHeight: 1.5,
            }}
          >
            <strong>Treat this token like a password.</strong> Anyone who has it can read your
            journal. Don&apos;t paste it into chat, screenshots, or shared docs.
          </div>
          <div style={cmdRowStyle}>
            <code
              className="step-cmd"
              style={{
                ...cmdCodeStyle,
                color: token ? 'var(--ink)' : 'var(--ink-3)',
              }}
            >
              {token ? token.token : 'kdr_••••••••••••••••••••••••'}
            </code>
            <Button variant="secondary" onClick={() => void mint()}>
              {token ? 'Rotate' : 'Mint token'}
            </Button>
            {token && (
              <Button variant="secondary" onClick={() => void copy(token.token)}>
                {copied ? 'Copied' : 'Copy'}
              </Button>
            )}
          </div>
          {token?.expires_at && (
            <p
              style={{
                fontSize: 12,
                color: 'var(--ink-3)',
                margin: 'var(--sp-2) 0 0',
              }}
            >
              Expires {new Date(token.expires_at).toLocaleDateString()}
            </p>
          )}
          {error && (
            <p
              style={{
                color: 'var(--rust)',
                fontSize: 13,
                margin: 'var(--sp-3) 0 0',
              }}
            >
              {error}
            </p>
          )}
        </li>

        {/* Step 3 — Set up your AI assistant */}
        <li className="step">
          <div className="step-num">
            <span>Step 03</span>
            <span className="glyph">✶</span>
          </div>
          <h3>
            Set up your <em>AI assistant</em>
          </h3>
          <p>Pick your client below — the per-step instructions will adjust.</p>

          <div
            role="tablist"
            aria-label="AI client"
            style={{
              display: 'flex',
              gap: 0,
              borderBottom: '1px solid var(--border)',
              marginTop: 'var(--sp-4)',
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
            <div style={{ ...cmdRowStyle, marginTop: 0 }}>
              <code
                className="step-cmd"
                style={{ ...cmdCodeStyle, wordBreak: 'break-word' }}
              >
                {ONE_LINER}
              </code>
              <Button variant="secondary" onClick={() => void copy(ONE_LINER)}>
                Copy
              </Button>
            </div>

            <div className="entry-section-eye" style={{ marginTop: 'var(--sp-4)' }}>
              Step 3 · Test it
            </div>
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
              style={{
                color: 'var(--terracotta)',
                fontSize: 14,
                display: 'inline-block',
                marginTop: 'var(--sp-3)',
              }}
            >
              Official docs →
            </a>
          </div>
        </li>
      </ol>
    </>
  )
}
