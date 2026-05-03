import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const css = readFileSync(resolve(__dirname, '../index.css'), 'utf8')

describe('button CSS contract (issue #23)', () => {
  it('defines a .btn base rule that includes white-space: nowrap', () => {
    const baseMatch = css.match(/\.btn\s*\{([^}]*)\}/)
    expect(baseMatch).not.toBeNull()
    expect(baseMatch![1]).toContain('white-space: nowrap')
  })

  it.each([
    'btn-primary',
    'btn-secondary',
    'btn-ghost',
    'btn-danger',
    'btn-link',
  ])('defines .%s rule', (cls) => {
    expect(css).toMatch(new RegExp(`\\.${cls}\\s*\\{`))
  })

  it.each(['btn-sm', 'btn-md', 'btn-lg'])('defines .%s rule', (cls) => {
    expect(css).toMatch(new RegExp(`\\.${cls}\\s*\\{`))
  })

  it('defines .btn:focus-visible with outline declaration', () => {
    const match = css.match(/\.btn:focus-visible\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toMatch(/outline\s*:/)
  })

  it('defines .btn:disabled rule', () => {
    expect(css).toMatch(/\.btn:disabled\s*\{/)
  })

  it('contains a @media (prefers-reduced-motion: reduce) block', () => {
    expect(css).toMatch(/@media\s*\(\s*prefers-reduced-motion:\s*reduce\s*\)/)
  })
})
