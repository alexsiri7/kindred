import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { MemoryRouter } from 'react-router'

import { Privacy } from '../Privacy'

describe('Privacy', () => {
  it('renders the required GDPR section labels', () => {
    render(
      <MemoryRouter>
        <Privacy />
      </MemoryRouter>,
    )
    expect(
      screen.getByRole('heading', { level: 1, name: /journal/i }),
    ).toBeInTheDocument()
    expect(screen.getByText(/last updated:/i)).toBeInTheDocument()
    expect(screen.getByText(/lawful basis/i)).toBeInTheDocument()
    expect(screen.getAllByText(/Supabase/i).length).toBeGreaterThan(0)
    expect(screen.getAllByText(/Samaritans/i).length).toBeGreaterThan(0)
    expect(screen.getByText(/ico\.org\.uk/i)).toBeInTheDocument()
  })

  it('renders the nav-brand wordmark in the page header', () => {
    const { container } = render(
      <MemoryRouter>
        <Privacy />
      </MemoryRouter>,
    )
    const navBrand = container.querySelector('.nav-brand')
    expect(navBrand).toBeInTheDocument()
    expect(navBrand?.querySelector('.wm em')?.textContent).toBe('Kindred')
    expect(navBrand?.querySelector('.wm .dot')?.textContent).toBe('.')
  })
})
