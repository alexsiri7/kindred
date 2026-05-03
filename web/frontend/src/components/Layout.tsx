import { useMemo } from 'react'
import { Link, Navigate, Outlet, useLocation, useNavigate } from 'react-router'
import { useAuth } from '../store/auth'
import { supabase } from '../lib/supabase'
import { KindredMark } from './Brand'
import { CrisisDisclaimerModal } from './CrisisDisclaimerModal'

type IconName = 'book' | 'layers' | 'search' | 'settings' | 'plug' | 'flag'

function Icon({ name, size = 16 }: { name: IconName; size?: number }) {
  const paths: Record<IconName, React.ReactNode> = {
    book: (
      <>
        <path d="M4 4v16a2 2 0 0 0 2 2h14" />
        <path d="M4 4h14v18" />
        <path d="M8 8h6M8 12h6M8 16h4" />
      </>
    ),
    layers: (
      <>
        <path d="M12 2L2 8l10 6 10-6-10-6z" />
        <path d="M2 14l10 6 10-6" />
      </>
    ),
    search: (
      <>
        <circle cx="11" cy="11" r="7" />
        <path d="M21 21l-5-5" />
      </>
    ),
    settings: (
      <>
        <circle cx="12" cy="12" r="3" />
        <path d="M19.4 15a1.7 1.7 0 0 0 .3 1.8l.1.1a2 2 0 1 1-2.8 2.8l-.1-.1a1.7 1.7 0 0 0-1.8-.3 1.7 1.7 0 0 0-1 1.5V21a2 2 0 0 1-4 0v-.1a1.7 1.7 0 0 0-1-1.5 1.7 1.7 0 0 0-1.8.3l-.1.1a2 2 0 1 1-2.8-2.8l.1-.1a1.7 1.7 0 0 0 .3-1.8 1.7 1.7 0 0 0-1.5-1H3a2 2 0 0 1 0-4h.1a1.7 1.7 0 0 0 1.5-1 1.7 1.7 0 0 0-.3-1.8l-.1-.1a2 2 0 1 1 2.8-2.8l.1.1a1.7 1.7 0 0 0 1.8.3h.1a1.7 1.7 0 0 0 1-1.5V3a2 2 0 0 1 4 0v.1a1.7 1.7 0 0 0 1 1.5 1.7 1.7 0 0 0 1.8-.3l.1-.1a2 2 0 1 1 2.8 2.8l-.1.1a1.7 1.7 0 0 0-.3 1.8v.1a1.7 1.7 0 0 0 1.5 1H21a2 2 0 0 1 0 4h-.1a1.7 1.7 0 0 0-1.5 1z" />
      </>
    ),
    plug: (
      <>
        <path d="M9 2v6" />
        <path d="M15 2v6" />
        <path d="M5 8h14v3a7 7 0 0 1-14 0z" />
        <path d="M12 18v4" />
      </>
    ),
    flag: (
      <>
        <path d="M4 22V4" />
        <path d="M4 4h13l-2 4 2 4H4" />
      </>
    ),
  }
  return (
    <svg
      className="ico"
      width={size}
      height={size}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      {paths[name]}
    </svg>
  )
}

const GITHUB_ISSUE_URL_BASE = 'https://github.com/alexsiri7/kindred/issues/new'

function buildGitHubIssueUrl(pagePath: string): string {
  const url = new URL(GITHUB_ISSUE_URL_BASE)
  url.searchParams.set('template', 'bug_report.md')
  // Keep body well under ~8 KB — GitHub returns HTTP 414 above that
  // (github/docs#5136). Do NOT add console logs, redux state, or screenshots.
  // Pathname only — query strings / fragments may carry per-user search terms
  // or future tokens and would leak into a public issue.
  url.searchParams.set(
    'body',
    [
      '## What happened',
      '',
      '<!-- Describe the bug -->',
      '',
      '## Context',
      `- **Page:** ${pagePath}`,
      `- **Browser:** ${navigator.userAgent}`,
    ].join('\n'),
  )
  return url.toString()
}

export function Layout() {
  const session = useAuth((s) => s.session)
  const location = useLocation()
  const navigate = useNavigate()
  const reportIssueUrl = useMemo(
    () => buildGitHubIssueUrl(location.pathname),
    [location.pathname],
  )

  if (!session) {
    return <Navigate to="/login" replace />
  }

  const email = session?.user?.email ?? ''
  const name = email.split('@')[0] ?? 'User'
  const initial = (name[0] ?? '?').toUpperCase()

  const isActive = (path: string) => {
    if (path === '/app') return location.pathname === '/app'
    return location.pathname.startsWith(path)
  }

  const libraryItems: { path: string; label: string; icon: IconName }[] = [
    { path: '/app', label: 'Entries', icon: 'book' },
    { path: '/app/patterns', label: 'Patterns', icon: 'layers' },
    { path: '/app/search', label: 'Search', icon: 'search' },
  ]

  const accountItems: { path: string; label: string; icon: IconName }[] = [
    { path: '/app/connect', label: 'Connect', icon: 'plug' },
    { path: '/app/settings', label: 'Settings', icon: 'settings' },
  ]

  return (
    <div className="app">
      <aside className="side">
        <Link to="/app" className="side-brand">
          <KindredMark size={26} />
          <span className="wm">
            <em>Kindred</em>
            <span className="dot">.</span>
          </span>
        </Link>

        <div className="side-search" onClick={() => void navigate('/app/search')} style={{ cursor: 'pointer' }}>
          <Icon name="search" size={14} />
          <input placeholder="Search by feeling, theme…" readOnly />
          <span className="kbd">⌘K</span>
        </div>

        <div className="side-eye">Library</div>
        <nav className="side-nav">
          {libraryItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`side-link ${isActive(item.path) ? 'is-active' : ''}`}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>

        <div className="side-eye">Account</div>
        <nav className="side-nav">
          {accountItems.map((item) => (
            <Link
              key={item.path}
              to={item.path}
              className={`side-link ${isActive(item.path) ? 'is-active' : ''}`}
            >
              <Icon name={item.icon} />
              <span>{item.label}</span>
            </Link>
          ))}
        </nav>

        <div className="side-eye">Help</div>
        <nav className="side-nav">
          <a
            href={reportIssueUrl}
            target="_blank"
            rel="noopener noreferrer"
            className="side-link"
          >
            <Icon name="flag" />
            <span>Report an issue</span>
          </a>
        </nav>

        <div className="side-foot">
          <div className="side-avatar">{initial}</div>
          <div className="who">
            {name}
            <small>{email}</small>
          </div>
          <button
            type="button"
            onClick={() => void supabase.auth.signOut()}
            style={{
              marginLeft: 'auto',
              background: 'none',
              border: 'none',
              cursor: 'pointer',
              fontFamily: 'var(--font-mono)',
              fontSize: '10px',
              color: 'var(--ink-3)',
              letterSpacing: '0.08em',
              textTransform: 'uppercase',
              padding: '4px',
            }}
            title="Sign out"
          >
            ↩
          </button>
        </div>
      </aside>

      <main className="main">
        <Outlet />
        <CrisisDisclaimerModal />
      </main>
    </div>
  )
}
