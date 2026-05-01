import * as Sentry from '@sentry/react'

if (import.meta.env.VITE_SENTRY_DSN) {
  try {
    Sentry.init({
      dsn: import.meta.env.VITE_SENTRY_DSN,
      integrations: [Sentry.browserTracingIntegration()],
      tracesSampleRate: 0.1,
      environment: 'production',
    })
  } catch (err) {
    console.warn('Sentry init failed; continuing without error reporting', err)
  }
}
