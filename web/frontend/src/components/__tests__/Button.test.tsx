import { describe, expect, it, vi } from 'vitest'
import { render, screen, fireEvent } from '@testing-library/react'
import { useRef, useEffect } from 'react'
import { Button } from '../Button'

describe('Button', () => {
  it('renders a <button> with class "btn btn-primary" by default', () => {
    render(<Button>Click me</Button>)
    const btn = screen.getByRole('button', { name: /click me/i })
    expect(btn.tagName).toBe('BUTTON')
    expect(btn).toHaveClass('btn', 'btn-primary')
  })

  it('variant="ghost" produces btn-ghost and not btn-primary', () => {
    render(<Button variant="ghost">Ghost</Button>)
    const btn = screen.getByRole('button')
    expect(btn).toHaveClass('btn', 'btn-ghost')
    expect(btn).not.toHaveClass('btn-primary')
  })

  it('size="lg" produces btn-lg; without size no size class is emitted', () => {
    const { rerender } = render(<Button size="lg">Large</Button>)
    expect(screen.getByRole('button')).toHaveClass('btn-lg')

    rerender(<Button>Default</Button>)
    const btn = screen.getByRole('button')
    expect(btn).not.toHaveClass('btn-sm')
    expect(btn).not.toHaveClass('btn-md')
    expect(btn).not.toHaveClass('btn-lg')
  })

  it('appends custom className without dropping base classes', () => {
    render(<Button className="extra">Click</Button>)
    const btn = screen.getByRole('button')
    expect(btn).toHaveClass('btn', 'btn-primary', 'extra')
  })

  it('forwards ref to the underlying HTMLButtonElement', () => {
    function Wrapper() {
      const ref = useRef<HTMLButtonElement>(null)
      useEffect(() => {
        if (ref.current) {
          ref.current.dataset.refOk = ref.current.tagName
        }
      })
      return <Button ref={ref}>Ref</Button>
    }
    render(<Wrapper />)
    const btn = screen.getByRole('button')
    expect(btn.dataset.refOk).toBe('BUTTON')
  })

  it('fires onClick when clicked', () => {
    const onClick = vi.fn()
    render(<Button onClick={onClick}>Click</Button>)
    fireEvent.click(screen.getByRole('button'))
    expect(onClick).toHaveBeenCalledTimes(1)
  })

  it('renders disabled attribute and suppresses click', () => {
    const onClick = vi.fn()
    render(
      <Button disabled onClick={onClick}>
        Click
      </Button>,
    )
    const btn = screen.getByRole('button')
    expect(btn).toBeDisabled()
    fireEvent.click(btn)
    expect(onClick).not.toHaveBeenCalled()
  })

  it('defaults type to "button"; passing type="submit" overrides', () => {
    const { rerender } = render(<Button>Default</Button>)
    expect(screen.getByRole('button')).toHaveAttribute('type', 'button')

    rerender(<Button type="submit">Submit</Button>)
    expect(screen.getByRole('button')).toHaveAttribute('type', 'submit')
  })
})
