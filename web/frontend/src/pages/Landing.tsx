import { useEffect, useRef, useState } from 'react'
import { Link } from 'react-router'
import { KindredWordmark } from '../components/Brand'
import { useAuth } from '../store/auth'

/* ============================================================
   Nav
   ============================================================ */
function Nav() {
  const session = useAuth((s) => s.session)
  return (
    <nav className="nav">
      <Link to="/" style={{ textDecoration: 'none' }}>
        <KindredWordmark markSize={26} />
      </Link>
      <div className="nav-links">
        <a href="#how" className="nav-link">How it works</a>
        <a href="#demo" className="nav-link">Demo</a>
        <a href="#patterns" className="nav-link">Patterns</a>
        <Link to="/privacy" className="nav-link">Privacy</Link>
      </div>
      <div className="nav-cta">
        {session
          ? <Link to="/app" className="nav-link">Open app</Link>
          : <Link to="/login" className="nav-link">Sign in</Link>
        }
        <Link to="/app" className="btn btn-primary btn-sm">Connect your AI</Link>
      </div>
    </nav>
  )
}

/* ============================================================
   Hero
   ============================================================ */
function Hero() {
  return (
    <section className="hero" id="home">
      <div className="hero-grid">
        <div className="hero-text">
          <div className="eyebrow">
            <span className="glyph">✶</span> Reflective journaling, via your AI assistant
          </div>
          <h1 className="hero-head">
            <span className="ink">A journal that</span>
            <br />
            <em>listens</em> <span className="ink">first.</span>
          </h1>
          <p className="hero-lede">
            Kindred is reflective journaling through your AI assistant — you talk, it stays with you.
            Your AI is the conversation; Kindred is the memory and the structure.
            No mood scores, no streaks, no nudges. Just a quiet companion that remembers.
          </p>
          <div className="hero-ctas">
            <button
              className="btn btn-primary btn-lg"
              type="button"
              onClick={() =>
                document.getElementById('demo')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
              }
            >
              See a session
            </button>
            <button
              className="btn btn-link btn-md"
              type="button"
              onClick={() =>
                document.getElementById('how')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
              }
            >
              How it works →
            </button>
          </div>
          <div className="hero-meta">
            <span>
              <span className="dot">◉</span> MCP server
            </span>
            <span>✶ Read-only web app</span>
            <span>· Your data, your vocabulary</span>
          </div>
        </div>

        <div className="hero-art" aria-hidden="true">
          <div className="hero-orbit">
            <img src="/illustration-orbit.svg" alt="" />
          </div>

          <div className="entry-peek entry-peek-1">
            <div className="meta">
              <span>Apr 28 · Tue</span>
              <span className="mood">◉ tender</span>
            </div>
            <h4>The Sunday-dread one, again</h4>
            <p>
              I noticed it earlier today than usual — somewhere around three. Not catastrophic.
              More like a draft under a door.
            </p>
            <div className="tags">
              <span className="tag-pill">sunday dread</span>
              <span className="tag-pill">3rd this month</span>
            </div>
          </div>

          <div className="entry-peek entry-peek-2">
            <div className="meta">
              <span>Apr 23 · Thu</span>
              <span className="mood" style={{ color: 'var(--moss)' }}>
                ◉ light
              </span>
            </div>
            <h4>A good walk</h4>
            <p>I think the trick is to go before I have a reason.</p>
          </div>
        </div>
      </div>
    </section>
  )
}

/* ============================================================
   How it works
   ============================================================ */
function HowItWorks() {
  return (
    <section className="how" id="how">
      <div className="wrap">
        <div className="section-head center">
          <div className="eyebrow">
            <span className="glyph">✶</span> How it works
          </div>
          <h2 className="section-title">
            Three small <em>moments</em>. One quiet practice.
          </h2>
          <p className="section-sub">
            Kindred lives inside your AI assistant as an MCP connector. Add it once, and three slash commands
            appear — one to begin, one to look at a pattern, one to close.
          </p>
        </div>

        <div className="steps">
          <div className="step">
            <div className="step-num">
              <span>Step 01</span>
              <span className="glyph">✶</span>
            </div>
            <h3>
              <em>Begin</em> with a gentle question
            </h3>
            <p>
              Your AI greets you with one open prompt — &ldquo;How are you arriving today?&rdquo; —
              and stays in listening mode. No advice, no reframing, no silver linings.
            </p>
          </div>
          <div className="step">
            <div className="step-num">
              <span>Step 02</span>
              <span className="glyph">✶</span>
            </div>
            <h3>
              Examine a <em>pattern</em>, only if you want to
            </h3>
            <p>
              When something feels worth pinning down, walk it through the four quadrants. Name the
              pattern in your own words. Kindred remembers it for next time.
            </p>
          </div>
          <div className="step">
            <div className="step-num">
              <span>Step 03</span>
              <span className="glyph">✶</span>
            </div>
            <h3>
              <em>Close</em> the session, gently
            </h3>
            <p>
              Your AI offers a one-paragraph summary in your language. You approve it. The entry
              saves. No homework, no streak, no &ldquo;see you tomorrow!&rdquo;.
            </p>
          </div>
        </div>
      </div>
    </section>
  )
}

/* ============================================================
   Conversation demo
   ============================================================ */
type ScriptItem =
  | { kind: 'user' | 'kindred'; from: string; text: React.ReactNode; delay: number }
  | { kind: 'tool'; delay: number; name: string; args: string; result: string }

const SCRIPT: ScriptItem[] = [
  {
    kind: 'user',
    from: 'You',
    delay: 600,
    text: <p>Hey.</p>,
  },
  {
    kind: 'kindred',
    from: 'Kindred',
    delay: 900,
    text: (
      <p>
        <em>Hey. No agenda from my side — what&apos;s here for you right now?</em>
      </p>
    ),
  },
  {
    kind: 'user',
    from: 'You',
    delay: 1100,
    text: (
      <p>
        It&apos;s that Sunday feeling again, even though it&apos;s Thursday. A kind of low
        static. I keep refreshing my email like that&apos;ll fix it.
      </p>
    ),
  },
  {
    kind: 'kindred',
    from: 'Kindred',
    delay: 1300,
    text: (
      <>
        <p>That sounds tiring — the static and the refreshing both.</p>
        <p>
          You said <em>&ldquo;Sunday feeling&rdquo;</em>, even on a Thursday. I&apos;m curious
          what makes it feel like that one in particular, if you want to sit with it for a moment.
        </p>
      </>
    ),
  },
  {
    kind: 'user',
    from: 'You',
    delay: 1200,
    text: (
      <p>
        I think it&apos;s the part where I&apos;m bracing for something I can&apos;t name. Like
        there&apos;s a thing on my list I&apos;ve forgotten and I won&apos;t know until it&apos;s
        too late.
      </p>
    ),
  },
  {
    kind: 'kindred',
    from: 'Kindred',
    delay: 1300,
    text: (
      <p>
        Bracing for an unnamed thing. That&apos;s a lot to carry quietly. Do you want to keep
        talking about it as it is, or look at it more structurally — thoughts, emotions, body —
        if it&apos;d help.
      </p>
    ),
  },
  {
    kind: 'user',
    from: 'You',
    delay: 800,
    text: <p>Yeah, let&apos;s look at it.</p>,
  },
  {
    kind: 'tool',
    delay: 700,
    name: 'list_patterns',
    args: '()',
    result: '→ ["sunday dread", "the letting-people-down spiral"]',
  },
  {
    kind: 'kindred',
    from: 'Kindred',
    delay: 1100,
    text: (
      <p>
        Okay. Take it slow. <em>What were you telling yourself</em>, just before the static showed
        up?
      </p>
    ),
  },
  {
    kind: 'user',
    from: 'You',
    delay: 1100,
    text: (
      <p>
        Something like — &ldquo;you&apos;re going to drop a ball and not realise.&rdquo; Plus a
        quieter one underneath: &ldquo;people will be polite about it but they&apos;ll notice.&rdquo;
      </p>
    ),
  },
  {
    kind: 'kindred',
    from: 'Kindred',
    delay: 1300,
    text: (
      <p>
        Thank you for naming both. The quieter one feels like it has more weight. And in your body
        — anything noticeable? Shoulders, breath, anywhere?
      </p>
    ),
  },
  {
    kind: 'user',
    from: 'You',
    delay: 1000,
    text: <p>Shallow breath. And my jaw is doing a thing.</p>,
  },
  {
    kind: 'kindred',
    from: 'Kindred',
    delay: 1300,
    text: (
      <p>
        Does this feel like the <em>&ldquo;Sunday dread&rdquo;</em> one you&apos;ve named before,
        or something new?
      </p>
    ),
  },
  { kind: 'user', from: 'You', delay: 900, text: <p>Same one. Definitely.</p> },
  {
    kind: 'tool',
    delay: 700,
    name: 'log_occurrence',
    args: '(pattern_name: "sunday dread", thoughts, emotions, …)',
    result: '✓ saved · 4th occurrence',
  },
  {
    kind: 'kindred',
    from: 'Kindred',
    delay: 1100,
    text: <p>Logged. Want to keep talking, or close out for now?</p>,
  },
]

function Conversation() {
  const [step, setStep] = useState(0)
  const [playing, setPlaying] = useState(true)
  const [typing, setTyping] = useState(false)
  const bodyRef = useRef<HTMLDivElement>(null)
  const timerRef = useRef<ReturnType<typeof setTimeout> | null>(null)

  useEffect(() => {
    if (!playing) return
    if (step >= SCRIPT.length) return

    const item = SCRIPT[step]
    const showTyping = item.kind === 'kindred'
    if (showTyping) {
      setTyping(true)
      timerRef.current = setTimeout(() => {
        setTyping(false)
        setStep((s) => s + 1)
      }, item.delay)
    } else {
      timerRef.current = setTimeout(() => {
        setStep((s) => s + 1)
      }, item.delay)
    }
    return () => {
      if (timerRef.current) clearTimeout(timerRef.current)
    }
  }, [step, playing])

  useEffect(() => {
    const el = bodyRef.current
    if (el) el.scrollTop = el.scrollHeight
  }, [step, typing])

  const replay = () => {
    if (timerRef.current) clearTimeout(timerRef.current)
    setStep(0)
    setTyping(false)
    setPlaying(true)
  }

  const togglePlay = () => {
    if (step >= SCRIPT.length) {
      replay()
      return
    }
    setPlaying((p) => !p)
  }

  const visible = SCRIPT.slice(0, step)
  const done = step >= SCRIPT.length

  return (
    <section className="conversation" id="demo">
      <div className="conv-grid">
        <div className="conv-text">
          <div className="eyebrow">
            <span className="glyph">✶</span> A real session, more or less
          </div>
          <h2 className="section-title">
            It&apos;s your AI. With <em>somewhere</em> for it to land.
          </h2>
          <p className="section-sub">
            You journal by talking to your AI assistant. Kindred adds the parts a journal needs: a place to
            keep entries, a way to name recurring patterns, and tools that only run when you ask
            them to.
          </p>
          <ul className="conv-list">
            <li>
              <span className="mark">01</span>
              <span>
                <strong>Validation before analysis.</strong> The default stance is being-with, not
                problem-solving.
              </span>
            </li>
            <li>
              <span className="mark">02</span>
              <span>
                <strong>You own the vocabulary.</strong> Patterns are named in your words. The AI
                suggests; never imposes.
              </span>
            </li>
            <li>
              <span className="mark">03</span>
              <span>
                <strong>No surveillance.</strong> Past entries stay quiet unless you ask.
              </span>
            </li>
            <li>
              <span className="mark">04</span>
              <span>
                <strong>One write path.</strong> The web app reads. The conversation is where
                things are written.
              </span>
            </li>
          </ul>
          <div className="conv-ctrls">
            <button
              type="button"
              className={`conv-ctrl-btn ${playing && !done ? 'is-on' : ''}`}
              onClick={togglePlay}
            >
              {done ? '↻ Replay' : playing ? '❚❚ Pause' : '▶ Play'}
            </button>
            <button type="button" className="conv-ctrl-btn" onClick={replay}>
              ↻ Restart
            </button>
            <span
              style={{
                fontFamily: 'var(--font-mono)',
                fontSize: 11,
                color: 'var(--ink-3)',
                letterSpacing: '0.06em',
              }}
            >
              {Math.min(step, SCRIPT.length)} / {SCRIPT.length}
            </span>
          </div>
        </div>

        <div className="chat" role="region" aria-label="Demo conversation">
          <div className="chat-chrome">
            <div className="chrome-dots">
              <span />
              <span />
              <span />
            </div>
            <div className="chrome-title">
              <span className="lock">🔒</span>
              your-ai · journal — Thursday, 1:48 PM
            </div>
            <div className="chrome-mcp">
              <span className="pulse" />
              {' '}kindred · mcp
            </div>
          </div>

          <div className="chat-body" ref={bodyRef}>
            {visible.map((m, i) => {
              if (m.kind === 'tool') {
                return (
                  <div key={i} className="tool-call">
                    <div className="tc-head">
                      <span className="arrow">→</span>
                      <span>kindred mcp call</span>
                    </div>
                    <div>
                      <span className="tc-name">{m.name}</span>
                      <span className="tc-args">{m.args}</span>
                    </div>
                    <div className="tc-result">{m.result}</div>
                  </div>
                )
              }
              return (
                <div key={i} className={`msg ${m.kind}`}>
                  <div className="msg-avatar" aria-hidden="true">
                    {m.kind === 'kindred' ? 'K' : 'A'}
                  </div>
                  <div className="msg-body">
                    <span className="msg-from">{m.from}</span>
                    <div className="msg-text">{m.text}</div>
                  </div>
                </div>
              )
            })}
            {typing && (
              <div className="msg kindred">
                <div className="msg-avatar" aria-hidden="true">K</div>
                <div className="msg-body">
                  <span className="msg-from">Kindred</span>
                  <div className="typing">
                    <span />
                    <span />
                    <span />
                  </div>
                </div>
              </div>
            )}
          </div>

          <form className="chat-input" onSubmit={(e) => e.preventDefault()}>
            <span className="slash-hint">✶ just talk</span>
            <input
              type="text"
              placeholder={done ? "Tell Kindred when you're ready to wrap up…" : 'Or just keep talking.'}
            />
            <button type="submit" className="send-btn" aria-label="Send">
              <svg
                width="16"
                height="16"
                viewBox="0 0 24 24"
                fill="none"
                stroke="currentColor"
                strokeWidth="2.25"
                strokeLinecap="round"
                strokeLinejoin="round"
              >
                <path d="M5 12h14M13 6l6 6-6 6" />
              </svg>
            </button>
          </form>
        </div>
      </div>
    </section>
  )
}

/* ============================================================
   Patterns — Hot Cross Bun
   ============================================================ */
function PatternsSection() {
  return (
    <section className="patterns" id="patterns">
      <div className="wrap pat-grid">
        <div className="pat-text">
          <div className="eyebrow">
            <span className="glyph">✶</span> The Hot Cross Bun
          </div>
          <h2 className="section-title">
            A small framework, <em>only</em> when you reach for it.
          </h2>
          <p className="section-sub">
            Borrowed from CBT, used gently. Four quadrants — thoughts, emotions, behaviours, body
            — to help name what&apos;s actually here. You name the pattern. Kindred keeps a list.
          </p>

          <div className="pat-named">
            <div className="pat-named-h">A few you might name</div>
            <div className="pat-chips">
              <span className="pat-chip">
                <span className="dot" />
                Sunday dread <span className="count">×4</span>
              </span>
              <span className="pat-chip">
                <span className="dot" />
                The letting-people-down spiral <span className="count">×2</span>
              </span>
              <span className="pat-chip">
                <span className="dot" />
                3pm wall <span className="count">×7</span>
              </span>
              <span className="pat-chip">
                <span className="dot" />
                The one about my dad <span className="count">×1</span>
              </span>
              <span className="pat-chip">
                <span className="dot" />
                Pre-trip jangle <span className="count">×3</span>
              </span>
            </div>
          </div>
        </div>

        <div className="bun" aria-label="Hot Cross Bun framework">
          <div className="bun-q">
            <span className="q-eye">Quadrant 01</span>
            <span className="q-name">Thoughts</span>
            <span className="q-ex">&ldquo;What was I telling myself?&rdquo;</span>
          </div>
          <div className="bun-q">
            <span className="q-eye">Quadrant 02</span>
            <span className="q-name">Emotions</span>
            <span className="q-ex">&ldquo;How did I feel — your word, not a label.&rdquo;</span>
          </div>
          <div className="bun-q">
            <span className="q-eye">Quadrant 03</span>
            <span className="q-name">Behaviours</span>
            <span className="q-ex">&ldquo;What did I do, or not do?&rdquo;</span>
          </div>
          <div className="bun-q">
            <span className="q-eye">Quadrant 04</span>
            <span className="q-name">Body</span>
            <span className="q-ex">
              &ldquo;What was happening physically — breath, jaw, shoulders.&rdquo;
            </span>
          </div>
          <div className="bun-center">HCB</div>
        </div>
      </div>
    </section>
  )
}

/* ============================================================
   Privacy
   ============================================================ */
function Privacy() {
  return (
    <section className="privacy" id="privacy">
      <div className="wrap">
        <div className="section-head">
          <div className="eyebrow">
            <span className="glyph">✶</span> Boring privacy claims, kept honest
          </div>
          <h2 className="section-title">
            Your <em>journal</em>. Not our dataset.
          </h2>
        </div>
        <div className="privacy-grid">
          <div className="priv">
            <div className="priv-eye">01 / Encrypted at rest</div>
            <h4>Stored on Supabase, scoped to you.</h4>
            <p>
              Row-level security on every table — cross-user reads are physically impossible from
              app code, even if a query forgets a where-clause.
            </p>
          </div>
          <div className="priv">
            <div className="priv-eye">02 / No training</div>
            <h4>Your words don&apos;t train anything.</h4>
            <p>
              We don&apos;t train models, and we pick providers with no-training policies. We{' '}
              <em>don&apos;t</em> claim end-to-end — the LLM has to read what you write.
            </p>
          </div>
          <div className="priv">
            <div className="priv-eye">03 / No surveillance</div>
            <h4>The AI won&apos;t volunteer your past.</h4>
            <p>
              &ldquo;You&apos;ve felt this way 5 Sundays in a row&rdquo; — never. Past entries
              surface only when you ask for them, in the conversation or the web app.
            </p>
          </div>
          <div className="priv">
            <div className="priv-eye">04 / One way out</div>
            <h4>Export everything. Delete it all.</h4>
            <p>
              Two buttons in settings. Export gives a JSON dump of every entry, pattern, and
              occurrence. Delete is a hard cascade. No &ldquo;are you sure&rdquo; theatre.
            </p>
          </div>
        </div>
        <div style={{ marginTop: 'var(--sp-5)' }}>
          <Link to="/privacy" className="nav-link">
            Read the full policy →
          </Link>
        </div>
      </div>
    </section>
  )
}

/* ============================================================
   EndCap + Footer
   ============================================================ */
function EndCap() {
  return (
    <>
      <section className="endcap" id="start">
        <div className="endcap-inner">
          <div className="eyebrow" style={{ color: 'rgba(250,247,242,0.5)' }}>
            <span className="glyph" style={{ color: 'var(--terracotta-3)' }}>
              ✶
            </span>{' '}
            Ready when you are
          </div>
          <h2>
            Talk to your AI. Let <em>Kindred</em> hold the rest.
          </h2>
          <p>
            Add the connector to your AI assistant, sign in with Google, type{' '}
            <code
              style={{
                background: 'rgba(250,247,242,0.08)',
                color: 'var(--paper)',
                padding: '2px 6px',
                borderRadius: 4,
                fontFamily: 'var(--font-mono)',
                fontSize: 14,
              }}
            >
              /kindred-start
            </code>
            {' '}(or paste the one-liner from /connect). That&apos;s the whole onboarding.
          </p>
          <div style={{ display: 'flex', gap: 12, justifyContent: 'center', flexWrap: 'wrap' }}>
            <Link to="/app" className="btn btn-primary btn-lg">
              Connect Kindred
            </Link>
            <button
              type="button"
              className="btn btn-ghost btn-lg"
              style={{ color: 'var(--paper)', border: '1px solid rgba(250,247,242,0.25)' }}
              onClick={() =>
                document.getElementById('how')?.scrollIntoView({ behavior: 'smooth', block: 'start' })
              }
            >
              How it works →
            </button>
          </div>
        </div>
      </section>
      <footer className="foot">
        <div>
          <span style={{ color: 'var(--terracotta-3)' }}>✶</span> Kindred — a small thing made by
          InterstellarAI
        </div>
        <div>
          <Link to="/privacy">Privacy</Link>
          <a href="#">Terms</a>
          <a href="#">Field notes</a>
        </div>
        <div>Made in orbit · v0.1</div>
      </footer>
    </>
  )
}

/* ============================================================
   Landing page (assembled)
   ============================================================ */
export function Landing() {
  return (
    <div className="site">
      <Nav />
      <main>
        <Hero />
        <HowItWorks />
        <Conversation />
        <PatternsSection />
        <Privacy />
        <EndCap />
      </main>
    </div>
  )
}
