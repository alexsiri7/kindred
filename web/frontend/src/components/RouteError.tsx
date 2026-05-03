import * as Sentry from '@sentry/react'
import { useEffect } from 'react'
import { Link, isRouteErrorResponse, useRouteError } from 'react-router'

export function RouteError() {
  const error = useRouteError()

  useEffect(() => {
    if (!isRouteErrorResponse(error)) {
      Sentry.captureException(error)
    }
  }, [error])

  const is404 = isRouteErrorResponse(error) && error.status === 404

  return (
    <div
      style={{
        display: 'flex',
        flexDirection: 'column',
        alignItems: 'center',
        justifyContent: 'center',
        minHeight: '100vh',
        gap: '1rem',
        fontFamily: 'var(--font-sans, sans-serif)',
        color: 'var(--ink, #1a1a1a)',
        textAlign: 'center',
        padding: '2rem',
      }}
    >
      <h1 style={{ fontSize: '1.5rem', fontWeight: 600, margin: 0 }}>
        {is404 ? 'Page not found' : 'Something went wrong'}
      </h1>
      <p style={{ color: 'var(--ink-3, #888)', margin: 0 }}>
        {is404
          ? "We couldn't find the page you were looking for."
          : 'An unexpected error occurred. The team has been notified.'}
      </p>
      <div style={{ display: 'flex', gap: '0.75rem', marginTop: '0.5rem' }}>
        <button
          type="button"
          onClick={() => window.history.back()}
          style={{
            background: 'none',
            border: '1px solid var(--ink-3, #888)',
            borderRadius: '4px',
            padding: '0.5rem 1rem',
            cursor: 'pointer',
            fontFamily: 'inherit',
            fontSize: '0.875rem',
            color: 'var(--ink, #1a1a1a)',
          }}
        >
          ← Go back
        </button>
        <Link
          to="/app"
          style={{
            background: 'var(--terracotta, #c0533a)',
            color: '#fff',
            borderRadius: '4px',
            padding: '0.5rem 1rem',
            textDecoration: 'none',
            fontSize: '0.875rem',
          }}
        >
          Go to app
        </Link>
      </div>
    </div>
  )
}
