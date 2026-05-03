import type { CSSProperties, SVGProps } from 'react'

type KindredMarkProps = Omit<SVGProps<SVGSVGElement>, 'width' | 'height'> & {
  size?: number
  accent?: string
  ink?: string
  inverse?: boolean
  title?: string
}

export function KindredMark({
  size = 28,
  accent,
  ink,
  inverse = false,
  title,
  ...rest
}: KindredMarkProps) {
  const resolvedInk = ink ?? (inverse ? 'var(--paper)' : 'var(--ink)')
  const resolvedAccent = accent ?? 'var(--accent)'

  const ariaProps = title
    ? { role: 'img' as const, 'aria-label': title }
    : { 'aria-hidden': true as const }

  return (
    <svg
      {...rest}
      width={size}
      height={size}
      viewBox="0 0 64 64"
      fill="none"
      focusable="false"
      {...ariaProps}
    >
      <ellipse
        cx="32"
        cy="32"
        rx="28"
        ry="11"
        transform="rotate(-22 32 32)"
        stroke={resolvedInk}
        strokeOpacity="0.18"
        strokeWidth="1"
        strokeDasharray="2 4"
        fill="none"
      />
      <circle cx="24" cy="32" r="11" stroke={resolvedInk} strokeWidth="2" fill="none" />
      <circle cx="40" cy="32" r="11" stroke={resolvedAccent} strokeWidth="2" fill="none" />
      <circle cx="32" cy="32" r="2" fill={resolvedAccent} />
    </svg>
  )
}

type KindredWordmarkProps = {
  markSize?: number
  className?: string
  style?: CSSProperties
  inverse?: boolean
}

export function KindredWordmark({
  markSize = 28,
  // className replaces the default 'nav-brand' wholesale (does not merge);
  // pass 'side-brand' or another class for non-nav contexts.
  className = 'nav-brand',
  style,
  inverse = false,
}: KindredWordmarkProps) {
  const wrapperStyle = inverse ? { color: 'var(--paper)', ...style } : style
  return (
    <span className={className} style={wrapperStyle}>
      <KindredMark size={markSize} inverse={inverse} />
      <span className="wm">
        <em>Kindred</em>
        <span className="dot">.</span>
      </span>
    </span>
  )
}
