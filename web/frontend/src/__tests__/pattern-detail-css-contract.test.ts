import { describe, expect, it } from 'vitest'
import { readFileSync } from 'node:fs'
import { resolve } from 'node:path'

const css = readFileSync(resolve(__dirname, '../index.css'), 'utf8')

// Strip the shared `.typical::before, .typical::after { ... }` block so the
// per-pseudo regexes below cannot accidentally match it.
const cssWithoutShared = css.replace(
  /\.typical::before,\s*\.typical::after\s*\{[^}]*\}/,
  '',
)

describe('PatternDetail typical-shape crosshair contract (#28)', () => {
  it('.typical declares position: relative so absolute pseudos anchor to it', () => {
    const match = css.match(/\.typical\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('position: relative')
  })

  it('.typical::before, .typical::after share the spec common declarations', () => {
    const match = css.match(/\.typical::before,\s*\.typical::after\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain("content: ''")
    expect(match![1]).toContain('position: absolute')
    expect(match![1]).toContain('background: var(--ink)')
    expect(match![1]).toContain('pointer-events: none')
  })

  it('.typical::before paints the vertical 1px line at center inset 12% top/bottom', () => {
    const match = cssWithoutShared.match(/\.typical::before\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('left: 50%')
    expect(match![1]).toContain('top: 12%')
    expect(match![1]).toContain('bottom: 12%')
    expect(match![1]).toContain('width: 1px')
    expect(match![1]).toContain('transform: translateX(-0.5px)')
    expect(match![1]).toMatch(/opacity:\s*0?\.15/)
  })

  it('.typical::after paints the horizontal 1px line at center inset 12% left/right', () => {
    const match = cssWithoutShared.match(/\.typical::after\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('top: 50%')
    expect(match![1]).toContain('left: 12%')
    expect(match![1]).toContain('right: 12%')
    expect(match![1]).toContain('height: 1px')
    expect(match![1]).toContain('transform: translateY(-0.5px)')
    expect(match![1]).toMatch(/opacity:\s*0?\.15/)
  })
})

describe('PatternDetail timeline dashed-rule contract (#28)', () => {
  it('.timeline::before uses border-left dashed in --border-strong', () => {
    const match = css.match(/\.timeline::before\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('border-left: 1px dashed var(--border-strong)')
  })

  it('.timeline::before does not declare a background that would hide the dashes', () => {
    const match = css.match(/\.timeline::before\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).not.toMatch(/background:/)
  })

  it('.timeline::before does not declare an explicit width that would mask the border', () => {
    const match = css.match(/\.timeline::before\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).not.toMatch(/\bwidth:/)
  })

  it('.tl-item::before sets pointer-events: none so it does not eat timeline clicks', () => {
    const match = css.match(/\.tl-item::before\s*\{([^}]*)\}/)
    expect(match).not.toBeNull()
    expect(match![1]).toContain('pointer-events: none')
  })
})
