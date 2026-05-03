import { describe, expect, it, vi, beforeEach } from 'vitest'
import { render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter, Routes, Route } from 'react-router'

const { exchangeCodeForSession } = vi.hoisted(() => ({
  exchangeCodeForSession: vi.fn(),
}))
vi.mock('../../lib/supabase', () => ({
  supabase: { auth: { exchangeCodeForSession } },
}))

import { AuthCallback } from '../AuthCallback'

function renderAt(url: string) {
  // window.location.search is what AuthCallback reads (not the router's
  // location), so set it explicitly for each render.
  const u = new URL(url, 'http://localhost')
  Object.defineProperty(window, 'location', {
    value: { ...window.location, search: u.search, pathname: u.pathname },
    writable: true,
    configurable: true,
  })
  return render(
    <MemoryRouter initialEntries={[u.pathname + u.search]}>
      <Routes>
        <Route path="/auth/callback" element={<AuthCallback />} />
        <Route path="/app" element={<div>APP</div>} />
        <Route path="/login" element={<div>LOGIN</div>} />
      </Routes>
    </MemoryRouter>,
  )
}

describe('AuthCallback', () => {
  beforeEach(() => exchangeCodeForSession.mockReset())

  it('exchanges the PKCE code and navigates to /app on success', async () => {
    exchangeCodeForSession.mockResolvedValue({ error: null })
    renderAt('/auth/callback?code=abc123')
    await waitFor(() => expect(screen.getByText('APP')).toBeInTheDocument())
    expect(exchangeCodeForSession).toHaveBeenCalledWith('abc123')
  })

  it('redirects to /login when no code is present', async () => {
    renderAt('/auth/callback')
    await waitFor(() => expect(screen.getByText('LOGIN')).toBeInTheDocument())
    expect(exchangeCodeForSession).not.toHaveBeenCalled()
  })

  it('redirects to /login when the exchange fails', async () => {
    exchangeCodeForSession.mockResolvedValue({
      error: { message: 'bad code' },
    })
    renderAt('/auth/callback?code=abc123')
    await waitFor(() => expect(screen.getByText('LOGIN')).toBeInTheDocument())
  })

  it('forwards an OAuth provider error from the URL to /login', async () => {
    renderAt('/auth/callback?error=access_denied')
    await waitFor(() => expect(screen.getByText('LOGIN')).toBeInTheDocument())
    expect(exchangeCodeForSession).not.toHaveBeenCalled()
  })
})
