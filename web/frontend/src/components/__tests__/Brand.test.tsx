import { describe, expect, it } from 'vitest'
import { render, screen } from '@testing-library/react'
import { KindredMark, KindredWordmark } from '../Brand'

describe('KindredMark', () => {
  it('default colors are CSS variables, not hex literals', () => {
    const { container } = render(<KindredMark />)
    expect(container.innerHTML).not.toMatch(/#[0-9a-f]{3,8}/i)
    expect(container.innerHTML).toContain('var(--ink)')
    expect(container.innerHTML).toContain('var(--accent)')
  })

  it('title prop wires role="img" and aria-label', () => {
    render(<KindredMark title="Kindred" />)
    expect(screen.getByRole('img', { name: 'Kindred' })).toBeInTheDocument()
  })

  it('default mark is aria-hidden', () => {
    const { container } = render(<KindredMark />)
    const svg = container.querySelector('svg')
    expect(svg?.getAttribute('aria-hidden')).toBe('true')
    expect(screen.queryByRole('img')).toBeNull()
  })

  it('focusable="false" is set both with and without title', () => {
    const { container, rerender } = render(<KindredMark />)
    expect(container.querySelector('svg')?.getAttribute('focusable')).toBe('false')

    rerender(<KindredMark title="Kindred" />)
    expect(container.querySelector('svg')?.getAttribute('focusable')).toBe('false')
  })

  it('inverse swaps the ink default to var(--paper) but keeps accent', () => {
    const { container } = render(<KindredMark inverse />)
    expect(container.innerHTML).toContain('var(--paper)')
    expect(container.innerHTML).toContain('var(--accent)')
    expect(container.innerHTML).not.toContain('var(--ink)')
  })

  it('explicit ink prop wins over inverse', () => {
    const { container } = render(<KindredMark inverse ink="#000" />)
    expect(container.innerHTML).toContain('#000')
    expect(container.innerHTML).not.toContain('var(--paper)')
  })

  it('explicit accent prop wins over default token', () => {
    const { container } = render(<KindredMark accent="#abc" />)
    expect(container.innerHTML).toContain('#abc')
    expect(container.innerHTML).not.toContain('var(--accent)')
  })

  it('size prop sets svg width and height', () => {
    const { container } = render(<KindredMark size={64} />)
    const svg = container.querySelector('svg')
    expect(svg?.getAttribute('width')).toBe('64')
    expect(svg?.getAttribute('height')).toBe('64')
  })

  it('spreads remaining props onto the svg', () => {
    render(<KindredMark className="x" data-testid="m" />)
    const svg = screen.getByTestId('m')
    expect(svg).toHaveClass('x')
  })

  it('caller cannot override internal aria-hidden via spread', () => {
    const { container } = render(<KindredMark aria-hidden={false} />)
    expect(container.querySelector('svg')?.getAttribute('aria-hidden')).toBe('true')
  })

  it('caller cannot override internal role/aria-label set by title', () => {
    render(<KindredMark title="Kindred" role="presentation" aria-label="other" />)
    expect(screen.getByRole('img', { name: 'Kindred' })).toBeInTheDocument()
  })

  it('caller cannot override focusable="false"', () => {
    const { container } = render(<KindredMark focusable="true" />)
    expect(container.querySelector('svg')?.getAttribute('focusable')).toBe('false')
  })
})

describe('KindredWordmark', () => {
  it('default class is "nav-brand" and renders mark + wordmark structure', () => {
    const { container } = render(<KindredWordmark />)
    const root = container.firstElementChild as HTMLElement
    expect(root.tagName).toBe('SPAN')
    expect(root).toHaveClass('nav-brand')
    expect(root.querySelector('em')?.textContent).toBe('Kindred')
    expect(root.querySelector('span.dot')?.textContent).toBe('.')
    expect(root.querySelector('svg')?.getAttribute('aria-hidden')).toBe('true')
  })

  it('className override replaces (not appends) the default', () => {
    const { container } = render(<KindredWordmark className="side-brand" />)
    const root = container.firstElementChild as HTMLElement
    expect(root).toHaveClass('side-brand')
    expect(root).not.toHaveClass('nav-brand')
  })

  it('markSize is forwarded to the inner KindredMark', () => {
    const { container } = render(<KindredWordmark markSize={32} />)
    expect(container.querySelector('svg')?.getAttribute('width')).toBe('32')
  })

  it('inner mark stays aria-hidden so visible text supplies accessible name', () => {
    const { container } = render(<KindredWordmark />)
    expect(container.querySelector('svg')?.getAttribute('aria-hidden')).toBe('true')
    expect(screen.queryByRole('img')).toBeNull()
  })

  it('inverse forwards to inner mark and re-tints the wrapper text color', () => {
    const { container } = render(<KindredWordmark inverse />)
    const root = container.firstElementChild as HTMLElement
    expect(container.innerHTML).toContain('var(--paper)')
    expect(container.innerHTML).not.toContain('var(--ink)')
    expect(root).toHaveStyle({ color: 'var(--paper)' })
  })

  it('forwards style prop to the root span', () => {
    const { container } = render(<KindredWordmark style={{ marginTop: 4 }} />)
    const root = container.firstElementChild as HTMLElement
    expect(root.style.marginTop).toBe('4px')
  })
})
