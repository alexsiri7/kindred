import { describe, expect, it, vi, beforeEach } from 'vitest'
import { fireEvent, render, screen, waitFor } from '@testing-library/react'
import { MemoryRouter } from 'react-router'

const { signInWithOAuth } = vi.hoisted(() => ({ signInWithOAuth: vi.fn() }))
vi.mock('../../lib/supabase', () => ({
  supabase: { auth: { signInWithOAuth } },
}))
vi.mock('../../store/auth', () => ({
  useAuth: (selector: (s: { session: unknown }) => unknown) =>
    selector({ session: null }),
}))

import { Login } from '../Login'

describe('Login', () => {
  beforeEach(() => signInWithOAuth.mockReset())

  it('redirects OAuth back to /auth/callback (the PKCE-loop fix)', () => {
    signInWithOAuth.mockResolvedValue({ error: null })
    render(
      <MemoryRouter initialEntries={['/login']}>
        <Login />
      </MemoryRouter>,
    )
    fireEvent.click(screen.getByRole('button', { name: /sign in with google/i }))
    expect(signInWithOAuth).toHaveBeenCalledWith(
      expect.objectContaining({
        provider: 'google',
        options: expect.objectContaining({
          redirectTo: expect.stringMatching(/\/auth\/callback$/),
        }),
      }),
    )
  })

  it('surfaces ?error= from the URL as a role="alert" message', () => {
    render(
      <MemoryRouter initialEntries={['/login?error=access_denied']}>
        <Login />
      </MemoryRouter>,
    )
    expect(screen.getByRole('alert')).toHaveTextContent('access_denied')
  })

  it('does not render an alert when no error param is present', () => {
    render(
      <MemoryRouter initialEntries={['/login']}>
        <Login />
      </MemoryRouter>,
    )
    expect(screen.queryByRole('alert')).not.toBeInTheDocument()
  })

  it('shows an alert when signInWithOAuth resolves with an error', async () => {
    signInWithOAuth.mockResolvedValue({ error: { message: 'provider down' } })
    render(
      <MemoryRouter initialEntries={['/login']}>
        <Login />
      </MemoryRouter>,
    )
    fireEvent.click(screen.getByRole('button', { name: /sign in with google/i }))
    await waitFor(() =>
      expect(screen.getByRole('alert')).toHaveTextContent('provider down'),
    )
  })

})
