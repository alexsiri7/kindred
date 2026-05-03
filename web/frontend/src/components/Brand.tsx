type KindredMarkProps = {
  size?: number
  accent?: string
  ink?: string
}

export function KindredMark({ size = 28, accent = '#7C7AB5', ink = '#1A1A1A' }: KindredMarkProps) {
  return (
    <svg width={size} height={size} viewBox="0 0 64 64" fill="none" aria-hidden="true">
      {/* outer dashed orbit, faint */}
      <ellipse
        cx="32" cy="32" rx="28" ry="11"
        transform="rotate(-22 32 32)"
        stroke={ink} strokeOpacity="0.18" strokeWidth="1" strokeDasharray="2 4" fill="none"
      />
      {/* two interlocking rings */}
      <circle cx="24" cy="32" r="11" stroke={ink} strokeWidth="2" fill="none" />
      <circle cx="40" cy="32" r="11" stroke={accent} strokeWidth="2" fill="none" />
      {/* the meeting point */}
      <circle cx="32" cy="32" r="2" fill={accent} />
    </svg>
  )
}

type KindredWordmarkProps = {
  inverse?: boolean
}

export function KindredWordmark({ inverse = false }: KindredWordmarkProps) {
  const ink = inverse ? '#FAF7F2' : '#1A1A1A'
  return (
    <div className="nav-brand" style={{ color: ink }}>
      <KindredMark size={28} ink={ink} />
      <span className="wm">
        <em>Kindred</em><span className="dot">.</span>
      </span>
    </div>
  )
}
