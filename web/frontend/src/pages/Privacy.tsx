import { Link } from 'react-router'
import { KindredWordmark } from '../components/Brand'

const LAST_UPDATED = '2026-05-03'

function Section({
  eyebrow,
  title,
  children,
}: {
  eyebrow: string
  title: string
  children: React.ReactNode
}) {
  return (
    <section style={{ marginBottom: 'var(--sp-7)' }}>
      <div className="eyebrow" style={{ marginBottom: 'var(--sp-2)' }}>
        <span className="glyph">✶</span> {eyebrow}
      </div>
      <h2
        style={{
          fontFamily: 'var(--font-display)',
          fontSize: 'var(--fs-h3)',
          fontWeight: 400,
          margin: '0 0 var(--sp-3)',
        }}
      >
        {title}
      </h2>
      <div
        style={{
          color: 'var(--ink-2)',
          fontSize: 'var(--fs-md)',
          lineHeight: 1.65,
        }}
      >
        {children}
      </div>
    </section>
  )
}

export function Privacy() {
  return (
    <div style={{ minHeight: '100vh', background: 'var(--paper)' }}>
      <nav className="nav">
        <Link to="/" style={{ textDecoration: 'none' }}>
          <KindredWordmark markSize={26} />
        </Link>
        <div className="nav-cta">
          <Link to="/" className="nav-link">
            Back to home
          </Link>
        </div>
      </nav>

      <main className="wrap" style={{ padding: 'var(--sp-7) var(--sp-5)' }}>
        <div style={{ maxWidth: '68ch', margin: '0 auto' }}>
          <header style={{ marginBottom: 'var(--sp-7)' }}>
            <div className="eyebrow" style={{ marginBottom: 'var(--sp-3)' }}>
              <span className="glyph">✶</span> Privacy
            </div>
            <h1
              style={{
                fontFamily: 'var(--font-display)',
                fontSize: 'var(--fs-h1)',
                fontWeight: 400,
                lineHeight: 1.1,
                margin: '0 0 var(--sp-3)',
              }}
            >
              Your <em>journal</em>. Not our dataset.
            </h1>
            <p
              style={{
                color: 'var(--ink-3)',
                fontFamily: 'var(--font-mono)',
                fontSize: 13,
                letterSpacing: '0.04em',
                margin: 0,
              }}
            >
              Last updated: {LAST_UPDATED}
            </p>
          </header>

          <Section eyebrow="01" title="Who we are">
            <p>
              Kindred is operated by InterstellarAI. For privacy questions or to
              exercise your rights under UK/EU GDPR, contact us at{' '}
              <a href="mailto:privacy@interstellarai.net">
                privacy@interstellarai.net
              </a>
              .
            </p>
          </Section>

          <Section eyebrow="02" title="What we collect">
            <p>We store only what we need to run the journal:</p>
            <ul>
              <li>
                <strong>Journal entries</strong> — the words you write to the AI
                during a session, plus the AI&apos;s replies.
              </li>
              <li>
                <strong>Pattern names and occurrences</strong> — the names you
                give to recurring themes and the four-quadrant breakdowns you
                log against them.
              </li>
              <li>
                <strong>Optional full transcripts</strong> — only when the
                &ldquo;Save transcripts&rdquo; toggle in{' '}
                <code>/app/settings</code> is on.
              </li>
              <li>
                <strong>Authentication info</strong> — your email address, via
                Google OAuth.
              </li>
              <li>
                <strong>Connector tokens</strong> — random opaque strings used
                by your AI assistant&apos;s MCP connector to identify your account.
              </li>
            </ul>
          </Section>

          <Section
            eyebrow="03"
            title="Lawful basis for processing (UK GDPR Art. 6)"
          >
            <p>
              <strong>Contract (Art. 6(1)(b))</strong> — processing your entries,
              patterns, and account data is necessary to provide the journaling
              service you signed up for.
            </p>
            <p>
              <strong>Consent (Art. 6(1)(a))</strong> — for the optional
              transcript-saving toggle, which you can turn off at any time in{' '}
              <code>/app/settings</code>.
            </p>
          </Section>

          <Section eyebrow="04" title="Recipients and sub-processors">
            <p>
              <strong>Supabase</strong> — database hosting and authentication.
              See{' '}
              <a
                href="https://supabase.com/legal/dpa"
                target="_blank"
                rel="noopener noreferrer"
              >
                supabase.com/legal/dpa
              </a>{' '}
              and{' '}
              <a
                href="https://supabase.com/privacy"
                target="_blank"
                rel="noopener noreferrer"
              >
                supabase.com/privacy
              </a>
              . Supabase&apos;s own infrastructure providers (AWS, Google
              Cloud, Cloudflare, and others) handle the underlying layers; their
              canonical, current list lives at the Supabase DPA link above
              rather than being duplicated here.
            </p>
            <p>
              <strong>Sentry</strong> — error monitoring. We do not send journal
              content to Sentry; only error stack traces and request metadata.
            </p>
            <p>
              <strong>Your chosen AI provider</strong> (e.g. Anthropic Claude,
              OpenAI, etc.) — your conversation is sent to whichever provider
              you have connected via the MCP connector you set up.
              Kindred does not control that provider&apos;s data retention or
              training behaviour. Review your AI provider&apos;s privacy
              settings directly.
            </p>
          </Section>

          <Section eyebrow="05" title="An honest note on access and encryption">
            <p>
              Kindred staff with database access could in principle read your
              entries. We commit not to do so except as required to operate the
              service or by law. Data is encrypted in transit (TLS) and at rest
              at the disk level via Supabase. This is{' '}
              <strong>not end-to-end encryption</strong> — the service and your
              chosen AI provider need to read your entries to function.
            </p>
          </Section>

          <Section eyebrow="06" title="No model training by Kindred">
            <p>
              We do not train any model on your data, and we do not license your
              data to third parties for training. If we add embeddings later
              (for example, to power <code>/app/search</code>), the embedding
              provider will be named in this section.
            </p>
          </Section>

          <Section eyebrow="07" title="International transfers">
            <p>
              Supabase infrastructure may process data outside the UK and EEA.
              The{' '}
              <a
                href="https://supabase.com/legal/dpa"
                target="_blank"
                rel="noopener noreferrer"
              >
                Supabase Data Processing Addendum
              </a>{' '}
              covers Standard Contractual Clauses (SCCs) for these transfers.
            </p>
          </Section>

          <Section eyebrow="08" title="Retention">
            <p>
              Entries, patterns, and occurrences are retained until you delete
              them or your account. Use{' '}
              <code>/app/settings → Delete account</code> for a hard cascading
              delete across every table that references your user ID.
            </p>
          </Section>

          <Section eyebrow="09" title="Your rights (UK/EU GDPR)">
            <p>
              You have the right to: access, rectification, erasure,
              restriction, portability, objection, and (where consent is the
              basis) withdrawal of consent. You can export everything via{' '}
              <code>/app/settings → Export as JSON</code>, and exercise the
              other rights by emailing{' '}
              <a href="mailto:privacy@interstellarai.net">
                privacy@interstellarai.net
              </a>
              .
            </p>
          </Section>

          <Section eyebrow="10" title="Right to complain">
            <p>
              If you believe we&apos;ve mishandled your data, you can complain
              to the UK Information Commissioner&apos;s Office at{' '}
              <a
                href="https://ico.org.uk/make-a-complaint/"
                target="_blank"
                rel="noopener noreferrer"
              >
                ico.org.uk/make-a-complaint
              </a>
              .
            </p>
          </Section>

          <Section eyebrow="11" title="Automated decision-making">
            <p>
              Kindred performs no automated decision-making with legal or
              similarly significant effects on you.
            </p>
          </Section>

          <Section eyebrow="12" title="Crisis services">
            <p>
              Kindred is a journaling tool, not a crisis service. If you&apos;re
              in immediate distress, contact a crisis line or emergency
              services. In the UK, Samaritans is free at 116 123 (24/7) or at{' '}
              <a
                href="https://www.samaritans.org/"
                target="_blank"
                rel="noopener noreferrer"
              >
                samaritans.org
              </a>
              . Resources vary by country.
            </p>
          </Section>

          <Section eyebrow="13" title="Changes to this policy">
            <p>
              We will update this page when our practices change and bump the
              &ldquo;Last updated&rdquo; date above. Material changes will be
              communicated in-app.
            </p>
          </Section>
        </div>
      </main>
    </div>
  )
}
