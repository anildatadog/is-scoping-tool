import { useNavigate } from 'react-router-dom'

export function HomeScreen() {
  const nav = useNavigate()
  return (
    <div style={{ width: "100%" }}>
      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ fontSize: '24px', fontWeight: 700, letterSpacing: '-0.3px', margin: 0 }}>
          IS Scoping Tool
        </h1>
        <p style={{ color: 'var(--dd-text-muted)', fontSize: '14px', marginTop: '4px' }}>
          Size a Datadog Implementation Services engagement in minutes.
        </p>
      </div>

      <div style={{ display: 'grid', gridTemplateColumns: 'repeat(auto-fit, minmax(280px, 1fr))', gap: '16px' }}>
        <div
          onClick={() => nav('/estimate')}
          style={{
            background: 'white',
            border: '1px solid var(--dd-border)',
            borderRadius: '12px',
            padding: '20px',
            cursor: 'pointer',
            boxShadow: 'var(--dd-shadow)',
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLElement).style.boxShadow = 'var(--dd-shadow-md)'
            ;(e.currentTarget as HTMLElement).style.transform = 'translateY(-1px)'
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.boxShadow = 'var(--dd-shadow)'
            ;(e.currentTarget as HTMLElement).style.transform = 'translateY(0)'
          }}
        >
          <div style={{
            width: '36px', height: '36px',
            background: 'var(--dd-purple-light)',
            borderRadius: '8px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '18px', marginBottom: '12px',
          }}>⚡</div>
          <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--dd-text)', marginBottom: '6px' }}>
            Quick estimate
          </div>
          <div style={{ fontSize: '13px', color: 'var(--dd-text-muted)', lineHeight: 1.5, marginBottom: '8px' }}>
            Pick a motion, answer 3–5 questions, get a rough day range in under 2 minutes.
          </div>
          <div style={{ fontSize: '12px', color: '#9ca3af', fontStyle: 'italic', marginBottom: '16px' }}>
            Use before a discovery call or when you need a quick ballpark.
          </div>
          <button
            style={{
              width: '100%',
              background: 'white',
              color: 'var(--dd-text)',
              border: '1px solid var(--dd-border)',
              borderRadius: '7px',
              padding: '8px 16px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'background 0.15s, color 0.15s, border-color 0.15s',
            }}
            onMouseEnter={e => {
              const el = e.currentTarget as HTMLButtonElement
              el.style.background = 'var(--dd-purple)'
              el.style.color = 'white'
              el.style.borderColor = 'var(--dd-purple)'
            }}
            onMouseLeave={e => {
              const el = e.currentTarget as HTMLButtonElement
              el.style.background = 'white'
              el.style.color = 'var(--dd-text)'
              el.style.borderColor = 'var(--dd-border)'
            }}
          >
            Start estimate →
          </button>
        </div>

        <div
          onClick={() => nav('/scope')}
          style={{
            background: 'white',
            border: '1px solid var(--dd-border)',
            borderRadius: '12px',
            padding: '20px',
            cursor: 'pointer',
            boxShadow: 'var(--dd-shadow)',
            transition: 'all 0.15s ease',
          }}
          onMouseEnter={e => {
            (e.currentTarget as HTMLElement).style.boxShadow = 'var(--dd-shadow-md)'
            ;(e.currentTarget as HTMLElement).style.transform = 'translateY(-1px)'
          }}
          onMouseLeave={e => {
            (e.currentTarget as HTMLElement).style.boxShadow = 'var(--dd-shadow)'
            ;(e.currentTarget as HTMLElement).style.transform = 'translateY(0)'
          }}
        >
          <div style={{
            width: '36px', height: '36px',
            background: '#F3F4F6',
            borderRadius: '8px',
            display: 'flex', alignItems: 'center', justifyContent: 'center',
            fontSize: '18px', marginBottom: '12px',
          }}>🔍</div>
          <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--dd-text)', marginBottom: '6px' }}>
            Full scope
          </div>
          <div style={{ fontSize: '13px', color: 'var(--dd-text-muted)', lineHeight: 1.5, marginBottom: '8px' }}>
            Look up a Salesforce opportunity, answer diagnostic questions, get a full diagnosis and proposal.
          </div>
          <div style={{ fontSize: '12px', color: '#9ca3af', fontStyle: 'italic', marginBottom: '16px' }}>
            Use when you have an opp ID and need a defensible proposal to send.
          </div>
          <button
            style={{
              width: '100%',
              background: 'white',
              color: 'var(--dd-text)',
              border: '1px solid var(--dd-border)',
              borderRadius: '7px',
              padding: '8px 16px',
              fontSize: '13px',
              fontWeight: 600,
              cursor: 'pointer',
              transition: 'background 0.15s, color 0.15s, border-color 0.15s',
            }}
            onMouseEnter={e => {
              const el = e.currentTarget as HTMLButtonElement
              el.style.background = 'var(--dd-purple)'
              el.style.color = 'white'
              el.style.borderColor = 'var(--dd-purple)'
            }}
            onMouseLeave={e => {
              const el = e.currentTarget as HTMLButtonElement
              el.style.background = 'white'
              el.style.color = 'var(--dd-text)'
              el.style.borderColor = 'var(--dd-border)'
            }}
          >
            Look up opportunity →
          </button>
        </div>
      </div>
    </div>
  )
}
