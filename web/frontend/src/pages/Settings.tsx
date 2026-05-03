import { useEffect, useState } from 'react'
import { api, type UserSettings } from '../api/client'

function Toggle({
  on,
  onChange,
  label,
}: {
  on: boolean
  onChange: (val: boolean) => void
  label: string
}) {
  return (
    <label className={`toggle ${on ? 'on' : ''}`} onClick={() => onChange(!on)}>
      <span className="toggle-track">
        <span className="toggle-thumb" />
      </span>
      <span className="toggle-label">{label}</span>
    </label>
  )
}

function DownloadIcon() {
  return (
    <svg
      width={14}
      height={14}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M21 15v4a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2v-4" />
      <path d="M7 10l5 5 5-5" />
      <path d="M12 15V3" />
    </svg>
  )
}

function TrashIcon() {
  return (
    <svg
      width={14}
      height={14}
      viewBox="0 0 24 24"
      fill="none"
      stroke="currentColor"
      strokeWidth="1.75"
      strokeLinecap="round"
      strokeLinejoin="round"
    >
      <path d="M3 6h18" />
      <path d="M8 6V4a2 2 0 0 1 2-2h4a2 2 0 0 1 2 2v2" />
      <path d="M19 6l-1 14a2 2 0 0 1-2 2H8a2 2 0 0 1-2-2L5 6" />
    </svg>
  )
}

export function Settings() {
  const [settings, setSettings] = useState<UserSettings | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [saving, setSaving] = useState(false)

  useEffect(() => {
    api
      .get<UserSettings>('/settings')
      .then(setSettings)
      .catch((e: Error) => setError(e.message))
  }, [])

  const save = async (patch: Partial<UserSettings>) => {
    setSaving(true)
    try {
      const next = await api.patch<UserSettings>('/settings', patch)
      setSettings(next)
    } catch (e) {
      setError((e as Error).message)
    } finally {
      setSaving(false)
    }
  }

  const exportData = async () => {
    const data = await api.get<unknown>('/export')
    const blob = new Blob([JSON.stringify(data, null, 2)], {
      type: 'application/json',
    })
    const url = URL.createObjectURL(blob)
    const a = document.createElement('a')
    a.href = url
    a.download = 'kindred-export.json'
    a.click()
    URL.revokeObjectURL(url)
  }

  const deleteAccount = async () => {
    if (
      !window.confirm(
        'Delete your account and all journal data? This cannot be undone.',
      )
    )
      return
    await api.delete('/account')
    window.location.href = '/login'
  }

  if (error) return <p style={{ color: 'var(--rust)' }}>{error}</p>
  if (!settings) return <p style={{ color: 'var(--ink-3)' }}>Loading…</p>

  return (
    <>
      <div className="page-head">
        <div className="page-eye">
          <span className="glyph">◈</span> Settings
        </div>
        <h1 className="page-title">
          Your <em>data</em>, your terms.
        </h1>
        <p className="page-sub">A few small toggles. Nothing else hidden behind submenus.</p>
      </div>

      <div className="set-section">
        <div>
          <div className="set-label">Timezone</div>
          <p className="set-help">Used for the &quot;user-local date&quot; of each entry.</p>
        </div>
        <div className="set-control">
          <input
            type="text"
            value={settings.timezone ?? ''}
            onChange={(e) => setSettings({ ...settings, timezone: e.target.value })}
            onBlur={(e) => void save({ timezone: e.target.value })}
            placeholder="America/New_York"
          />
          {saving && (
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                color: 'var(--ink-3)',
              }}
            >
              Saving…
            </span>
          )}
        </div>
      </div>

      <div className="set-section">
        <div>
          <div className="set-label">Save transcripts</div>
          <p className="set-help">
            Stores the full conversation alongside the summary.
          </p>
        </div>
        <div className="set-control">
          <Toggle
            on={settings.transcript_enabled}
            onChange={(val) => void save({ transcript_enabled: val })}
            label={
              settings.transcript_enabled
                ? 'On — summary + transcript'
                : 'Off — summary only'
            }
          />
        </div>
      </div>

      <div className="set-section">
        <div>
          <div className="set-label">Export everything</div>
          <p className="set-help">
            A JSON dump of every entry, pattern, and occurrence. Yours to take.
          </p>
        </div>
        <div className="set-control">
          <button
            type="button"
            className="btn btn-secondary"
            onClick={() => void exportData()}
          >
            <DownloadIcon /> Export as JSON
          </button>
        </div>
      </div>

      <div className="set-section">
        <div>
          <div className="set-label">Delete account</div>
          <p className="set-help">
            Hard delete, cascading across all tables.
          </p>
        </div>
        <div className="set-control">
          <button
            type="button"
            className="btn btn-danger"
            onClick={() => void deleteAccount()}
          >
            <TrashIcon /> Delete everything
          </button>
        </div>
      </div>
    </>
  )
}
