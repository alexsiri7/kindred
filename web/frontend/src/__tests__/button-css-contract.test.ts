import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const css = readFileSync(resolve(__dirname, '../index.css'), 'utf8')

describe('button CSS contract (issue #23)', () => {
  it('defines a .btn base rule that includes white-space: nowrap', () => {
    // Anchor to start-of-line so we match the base .btn rule, not a nested
    // .btn block (e.g., inside @media prefers-reduced-motion).
    const baseMatch = css.match(/^\.btn\s*\{([^}]*)\}/m)
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

  it.each(['btn-sm', 'btn-md', 'btn-lg'])(
    'defines .%s with padding and font-size declarations',
    (cls) => {
      const m = css.match(new RegExp(`\\.${cls}\\s*\\{([^}]*)\\}`))
      expect(m).not.toBeNull()
      expect(m![1]).toMatch(/padding\s*:/)
      expect(m![1]).toMatch(/font-size\s*:/)
    },
  )

  it('defines .btn:focus-visible with non-zero outline AND outline-offset', () => {
    const match = css.match(/\.btn:focus-visible\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    // Reject "outline: 0" — must be a positive width, otherwise WCAG 2.2 SC 1.4.11 regression.
    expect(match![1]).toMatch(/outline\s*:\s*[1-9]/)
    expect(match![1]).toMatch(/outline-offset\s*:/)
  })

  it('defines .btn:disabled with cursor and opacity declarations', () => {
    const m = css.match(/\.btn:disabled\s*\{([^}]*)\}/)
    expect(m).not.toBeNull()
    expect(m![1]).toMatch(/cursor\s*:\s*not-allowed/)
    expect(m![1]).toMatch(/opacity\s*:/)
  })

  it('@media (prefers-reduced-motion: reduce) disables .btn transitions', () => {
    const m = css.match(
      /@media\s*\(\s*prefers-reduced-motion:\s*reduce\s*\)\s*\{([\s\S]*?)\n\}/,
    )
    expect(m).not.toBeNull()
    expect(m![1]).toMatch(/\.btn\s*\{[^}]*transition\s*:\s*none/)
  })
})
