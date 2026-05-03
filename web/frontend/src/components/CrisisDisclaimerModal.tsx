import { useEffect, useRef, useState } from 'react'
import * as Sentry from '@sentry/react'
import { api, type UserSettings } from '../api/client'

export function CrisisDisclaimerModal() {
  const [settings, setSettings] = useState<UserSettings | null>(null)
  const [error, setError] = useState<string | null>(null)
  const [submitting, setSubmitting] = useState(false)
  const [dismissed, setDismissed] = useState(false)
  const dialogRef = useRef<HTMLDivElement | null>(null)

  useEffect(() => {
    api
      .get<UserSettings>('/settings')
      .then(setSettings)
      .catch((e) => {
        // Fail open: do not block the app on a settings outage,
        // but record so a regression that bypasses the disclaimer
        // for everyone is visible in telemetry.
        Sentry.captureException(e)
      })
  }, [])

  const isOpen =
    !dismissed && settings !== null && !settings.crisis_disclaimer_acknowledged_at

  useEffect(() => {
    if (!isOpen) return
    const dialog = dialogRef.current
    if (!dialog) return
    const handleKeyDown = (e: KeyboardEvent) => {
      if (e.key !== 'Tab') return
      const focusables = dialog.querySelectorAll<HTMLElement>(
        'a[href], button:not([disabled]), [tabindex]:not([tabindex="-1"])',
      )
      if (focusables.length === 0) return
      const first = focusables[0]
      const last = focusables[focusables.length - 1]
      const active = document.activeElement as HTMLElement | null
      if (e.shiftKey && (active === first || !dialog.contains(active))) {
        e.preventDefault()
        last.focus()
      } else if (!e.shiftKey && (active === last || !dialog.contains(active))) {
        e.preventDefault()
        first.focus()
      }
    }
    document.addEventListener('keydown', handleKeyDown)
    return () => document.removeEventListener('keydown', handleKeyDown)
  }, [isOpen])

  const acknowledge = async () => {
    setSubmitting(true)
    setError(null)
    try {
      const next = await api.patch<UserSettings>('/settings', {
        crisis_disclaimer_acknowledged_at: new Date().toISOString(),
      })
      setSettings(next)
      setDismissed(true)
    } catch (e) {
      Sentry.captureException(e)
      setError((e as Error).message)
    } finally {
      setSubmitting(false)
    }
  }

  if (!isOpen) return null

  return (
    <div
      ref={dialogRef}
      role="dialog"
      aria-modal="true"
      aria-labelledby="crisis-disclaimer-title"
      style={{
        position: 'fixed',
        inset: 0,
        zIndex: 1000,
        background: 'rgba(28,26,24,0.55)',
        display: 'flex',
        alignItems: 'center',
        justifyContent: 'center',
        padding: 'var(--sp-5)',
      }}
    >
      <div
        style={{
          width: '100%',
          maxWidth: 460,
          background: 'var(--bg-elevated)',
          border: '1px solid var(--border)',
          borderRadius: 'var(--r-xl)',
          padding: 'var(--sp-7)',
          boxShadow: 'var(--shadow-md)',
        }}
      >
        <h2
          id="crisis-disclaimer-title"
          style={{
            fontFamily: 'var(--font-display)',
            fontSize: 'var(--fs-h3)',
            fontWeight: 400,
            margin: '0 0 var(--sp-4)',
          }}
        >
          Before you begin
        </h2>
        <p
          style={{
            color: 'var(--ink-2)',
            fontSize: 'var(--fs-md)',
            lineHeight: 1.6,
            margin: '0 0 var(--sp-4)',
          }}
        >
          Kindred is a journaling tool, not a crisis service. If you&apos;re in
          immediate distress, please contact a crisis line or emergency services.
        </p>
        <p
          style={{
            color: 'var(--ink-2)',
            fontSize: 'var(--fs-sm)',
            lineHeight: 1.6,
            margin: '0 0 var(--sp-6)',
          }}
        >
          In the UK, you can call Samaritans free at 116 123 (24/7), or visit{' '}
          <a
            href="https://www.samaritans.org/"
            target="_blank"
            rel="noopener noreferrer"
          >
            samaritans.org
          </a>
          . Resources vary by country.
        </p>

        {error && (
          <p
            style={{
              color: 'var(--rust)',
              fontSize: 13,
              margin: '0 0 var(--sp-3)',
            }}
          >
            {error}
          </p>
        )}

        <button
          type="button"
          className="btn btn-primary btn-lg"
          autoFocus
          disabled={submitting}
          onClick={() => void acknowledge()}
          style={{ width: '100%', justifyContent: 'center' }}
        >
          {submitting ? 'Saving…' : 'I understand'}
        </button>
      </div>
    </div>
  )
}
