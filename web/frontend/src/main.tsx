import * as Sentry from '@sentry/react'
import { StrictMode } from 'react'
import { createRoot } from 'react-dom/client'
import { createBrowserRouter, RouterProvider } from 'react-router'
import './index.css'
import './lib/supabase'

if (import.meta.env.VITE_SENTRY_DSN) {
  Sentry.init({
    dsn: import.meta.env.VITE_SENTRY_DSN,
    integrations: [Sentry.browserTracingIntegration()],
    tracesSampleRate: 0.1,
    environment: 'production',
  })
}
import { Layout } from './components/Layout'
import { Login } from './pages/Login'
import { Home } from './pages/Home'
import { EntryDetail } from './pages/EntryDetail'
import { Patterns } from './pages/Patterns'
import { PatternDetail } from './pages/PatternDetail'
import { Search } from './pages/Search'
import { Settings } from './pages/Settings'
import { Connect } from './pages/Connect'
import { McpAuth } from './pages/McpAuth'

const router = createBrowserRouter([
  { path: '/mcp-auth', element: <McpAuth /> },
  {
    element: <Layout />,
    children: [
      { path: '/', element: <Home /> },
      { path: '/login', element: <Login /> },
      { path: '/entries/:id', element: <EntryDetail /> },
      { path: '/patterns', element: <Patterns /> },
      { path: '/patterns/:id', element: <PatternDetail /> },
      { path: '/search', element: <Search /> },
      { path: '/settings', element: <Settings /> },
      { path: '/connect', element: <Connect /> },
    ],
  },
])

const rootEl = document.getElementById('root')
if (!rootEl) throw new Error('#root element not found')
createRoot(rootEl).render(
  <StrictMode>
    <RouterProvider router={router} />
  </StrictMode>,
)
