import { describe, expect, it, vi } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'

vi.mock('../../store/auth', () => ({
  useAuth: (selector: (s: { session: unknown }) => unknown) =>
    selector({
      session: { user: { email: 'tester@example.com' } },
    }),
}))

vi.mock('../../lib/supabase', () => ({
  supabase: { auth: { signOut: vi.fn() } },
}))

import { Layout } from '../Layout'

describe('Layout — Report an issue link', () => {
  it('renders a sidebar link to the GitHub new-issue page', () => {
    render(
      <MemoryRouter initialEntries={['/app']}>
        <Layout />
      </MemoryRouter>,
    )

    const link = screen.getByRole('link', { name: /report an issue/i })
    expect(link).toBeInTheDocument()
    expect(link).toHaveAttribute('target', '_blank')
    expect(link).toHaveAttribute('rel', 'noopener noreferrer')

    const href = link.getAttribute('href') ?? ''
    expect(href).toMatch(/^https:\/\/github\.com\/alexsiri7\/kindred\/issues\/new\?/)
    expect(href).toContain('template=bug_report.md')
    expect(href).toContain('title=Bug')
    expect(decodeURIComponent(href)).toContain('Page:')
    expect(decodeURIComponent(href)).toContain('Browser:')
  })

  it('uses a native anchor (keyboard-activatable on Enter)', () => {
    render(
      <MemoryRouter initialEntries={['/app']}>
        <Layout />
      </MemoryRouter>,
    )
    const link = screen.getByRole('link', { name: /report an issue/i })
    expect(link.tagName).toBe('A')
  })
})
