import { describe, expect, it, vi, beforeEach, afterEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route, useSearchParams } from 'react-router'
import { StrictMode } from 'react'

const { exchangeCodeForSession, setSession } = vi.hoisted(() => ({
  exchangeCodeForSession: vi.fn(),
  setSession: vi.fn(),
}))
vi.mock('../../lib/supabase', () => ({
  supabase: { auth: { exchangeCodeForSession } },
}))
vi.mock('../../store/auth', () => ({
  useAuth: { getState: () => ({ setSession }) },
}))

import { AuthCallback } from '../AuthCallback'

function LoginStub() {
  const [params] = useSearchParams()
  return <div>LOGIN error={params.get('error') ?? ''}</div>
}

let originalLocation: Location
beforeEach(() => {
  originalLocation = window.location
  exchangeCodeForSession.mockReset()
  setSession.mockReset()
})
afterEach(() => {
  Object.defineProperty(window, 'location', {
    value: originalLocation,
    writable: true,
    configurable: true,
  })
})

function setLocation(url: string) {
  const u = new URL(url, 'http://localhost')
  Object.defineProperty(window, 'location', {
    value: { ...window.location, search: u.search, pathname: u.pathname },
    writable: true,
    configurable: true,
  })
  return u
}

function renderAt(url: string) {
  // window.location.search is what AuthCallback reads (not the router's
  // location), so set it explicitly for each render.
  const u = setLocation(url)
  return render(
    <MemoryRouter initialEntries={[u.pathname + u.search]}>
      <Routes>
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/app" element={<div>APP</div>} />
        <Route path="/login" element={<LoginStub />} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AuthCallback', () => {
  it('exchanges the PKCE code and navigates to /app on success', async () => {
    exchangeCodeForSession.mockResolvedValue({
      data: { session: { user: { email: 'tester@example.com' } } },
      error: null,
    })
    renderAt('/auth/callback?code=abc123')
    await waitFor(() => expect(screen.getByText('APP')).toBeInTheDocument())
    expect(exchangeCodeForSession).toHaveBeenCalledWith('abc123')
  })

  it('writes the session to the auth store before navigating (closes race with Layout gate)', async () => {
    const session = { user: { email: 'tester@example.com' } }
    exchangeCodeForSession.mockResolvedValue({ data: { session }, error: null })
    renderAt('/auth/callback?code=abc123')
    await waitFor(() => expect(screen.getByText('APP')).toBeInTheDocument())
    expect(setSession).toHaveBeenCalledWith(session)
  })

  it('redirects to /login with "Missing authorization code." when code absent', async () => {
    renderAt('/auth/callback')
    await waitFor(() =>
      expect(
        screen.getByText(/LOGIN error=Missing authorization code\./),
      ).toBeInTheDocument(),
    )
    expect(exchangeCodeForSession).not.toHaveBeenCalled()
  })

  it('redirects to /login with the exchange error message', async () => {
    exchangeCodeForSession.mockResolvedValue({
      data: { session: null },
      error: { message: 'bad code' },
    })
    renderAt('/auth/callback?code=abc123')
    await waitFor(() =>
      expect(screen.getByText(/LOGIN error=bad code/)).toBeInTheDocument(),
    )
  })

  it('redirects to /login when exchangeCodeForSession itself rejects', async () => {
    exchangeCodeForSession.mockRejectedValue(new Error('network down'))
    renderAt('/auth/callback?code=abc123')
    await waitFor(() =>
      expect(screen.getByText(/LOGIN error=network down/)).toBeInTheDocument(),
    )
  })

  it('forwards an OAuth provider error from the URL to /login', async () => {
    renderAt('/auth/callback?error=access_denied')
    await waitFor(() =>
      expect(
        screen.getByText(/LOGIN error=access_denied/),
      ).toBeInTheDocument(),
    )
    expect(exchangeCodeForSession).not.toHaveBeenCalled()
  })

  it('prefers error_description over error when both are present', async () => {
    renderAt(
      '/auth/callback?error=access_denied&error_description=The+user+denied+access',
    )
    await waitFor(() =>
      expect(
        screen.getByText(/LOGIN error=The user denied access/),
      ).toBeInTheDocument(),
    )
    expect(exchangeCodeForSession).not.toHaveBeenCalled()
  })

  it('does not double-exchange under StrictMode (PKCE codes are single-use)', async () => {
    exchangeCodeForSession.mockResolvedValue({
      data: { session: { user: { email: 'tester@example.com' } } },
      error: null,
    })
    const u = setLocation('/auth/callback?code=once')
    render(
      <StrictMode>
        <MemoryRouter initialEntries={[u.pathname + u.search]}>
          <Routes>
            <Route path="/auth/callback" element={<AuthCallback />} />
            <Route path="/app" element={<div>APP</div>} />
            <Route path="/login" element={<LoginStub />} />
          </Routes>
        </MemoryRouter>
      </StrictMode>,
    )
    await waitFor(() => expect(screen.getByText('APP')).toBeInTheDocument())
    expect(exchangeCodeForSession).toHaveBeenCalledTimes(1)
    expect(exchangeCodeForSession).toHaveBeenCalledWith('once')
  })
})
