import { useEffect, useState } from 'react'
import { api, type UserSettings } from '../api/client'

const ALL_TIMEZONES: string[] = Intl.supportedValuesOf('timeZone')

function TimezoneInput({
  value,
  onSave,
}: {
  value: string
  onSave: (tz: string) => void
}) {
  const [inputVal, setInputVal] = useState(value)
  const [open, setOpen] = useState(false)
  const [highlighted, setHighlighted] = useState(0)

  // keep local input in sync when parent value changes (e.g. after auto-detect save)
  useEffect(() => {
    setInputVal(value)
  }, [value])

  const suggestions = inputVal.trim()
    ? ALL_TIMEZONES.filter((tz) =>
        tz.toLowerCase().includes(inputVal.toLowerCase()),
      ).slice(0, 10)
    : []

  // reset highlighted index whenever the suggestion list changes
  useEffect(() => {
    setHighlighted(0)
  }, [suggestions.length, inputVal])

  const selectTz = (tz: string) => {
    setInputVal(tz)
    setOpen(false)
    onSave(tz)
  }

  const handleKeyDown = (e: React.KeyboardEvent<HTMLInputElement>) => {
    if (!open || suggestions.length === 0) return
    if (e.key === 'ArrowDown') {
      e.preventDefault()
      setHighlighted((h) => Math.min(h + 1, suggestions.length - 1))
    } else if (e.key === 'ArrowUp') {
      e.preventDefault()
      setHighlighted((h) => Math.max(h - 1, 0))
    } else if (e.key === 'Enter') {
      e.preventDefault()
      if (suggestions[highlighted]) selectTz(suggestions[highlighted])
    } else if (e.key === 'Escape') {
      setOpen(false)
    }
  }

  const showDropdown = open && suggestions.length > 0

  return (
    <div style={{ position: 'relative', width: 280 }}>
      <input
        type="text"
        value={inputVal}
        placeholder="America/New_York"
        onChange={(e) => {
          setInputVal(e.target.value)
          setOpen(true)
        }}
        onFocus={() => setOpen(true)}
        onBlur={(e) => {
          setOpen(false)
          onSave(e.target.value)
        }}
        onKeyDown={handleKeyDown}
        style={{ width: '100%' }}
      />
      {showDropdown && (
        <ul
          style={{
            position: 'absolute',
            top: '100%',
            left: 0,
            right: 0,
            marginTop: 4,
            padding: '4px 0',
            listStyle: 'none',
            background: 'var(--paper-2)',
            border: '1px solid var(--border)',
            borderRadius: 'var(--r-md)',
            boxShadow: 'var(--shadow-md)',
            zIndex: 50,
            overflow: 'hidden',
          }}
        >
          {suggestions.map((tz, i) => (
            <li
              key={tz}
              onMouseDown={(e) => {
                e.preventDefault() // prevent blur firing first
                selectTz(tz)
              }}
              style={{
                padding: '8px 12px',
                fontFamily: 'var(--font-mono)',
                fontSize: 12,
                letterSpacing: '0.02em',
                color: i === highlighted ? 'var(--ink)' : 'var(--ink-3)',
                background:
                  i === highlighted ? 'var(--paper-3)' : 'transparent',
                cursor: 'pointer',
              }}
              onMouseEnter={() => setHighlighted(i)}
            >
              {tz}
            </li>
          ))}
        </ul>
      )}
    </div>
  )
}

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
      .then((s) => {
        if (!s.timezone) {
          const detected = Intl.DateTimeFormat().resolvedOptions().timeZone
          const next = { ...s, timezone: detected }
          setSettings(next)
          void api
            .patch<UserSettings>('/settings', { timezone: detected })
            .then(setSettings)
            .catch((e: Error) => setError(e.message))
        } else {
          setSettings(s)
        }
      })
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
          <TimezoneInput
            value={settings.timezone ?? ''}
            onSave={(tz) => void save({ timezone: tz })}
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
