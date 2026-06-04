import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { useToken } from '../App'
import { useP1State } from '@/hooks/useP1State'

const P1_TO_P2: Record<string, string> = {
  obs: 'infra_apm_logs', dx: 'dx', security: 'security', ai: 'ai', finops: 'finops',
}

export function P1Result() {
  const { motion = '' } = useParams()
  const nav = useNavigate()
  const token = useToken()
  const { answers, reset } = useP1State()

  const { data: motions } = useQuery({ queryKey: ['phase1Motions'], queryFn: () => api.phase1Motions(token) })
  const { data: est, isLoading } = useQuery({
    queryKey: ['phase1Estimate', motion, answers],
    queryFn: () => api.phase1Estimate({ motion, answers }, token),
  })
  const { data: explain } = useQuery({
    queryKey: ['phase1Explain', motion, answers],
    queryFn: () => api.phase1Explain({ motion, answers }, token),
    enabled: !!est,
  })

  if (isLoading) return <p style={{ color: 'var(--dd-text-muted)', padding: '32px 0' }}>Calculating…</p>
  const m = motions?.[motion]

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <p style={{ fontSize: '11px', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.08em', marginBottom: '4px' }}>
          Phase 1 estimate · first-pass only
        </p>
        <h1 style={{ fontSize: '22px', fontWeight: 700, letterSpacing: '-0.3px', margin: 0 }}>{m?.label}</h1>
      </div>

      {est?.days_min != null ? (
        <div style={{ display: 'grid', gridTemplateColumns: 'repeat(3, 1fr)', gap: '12px', marginBottom: '20px' }}>
          {[
            { label: 'Recommended motion', value: m?.label },
            { label: 'Estimated days', value: `${est.days_min}–${est.days_max}` },
            { label: 'PM required?', value: est.pm_required ? 'Yes' : 'No', red: est.pm_required },
          ].map(({ label, value, red }) => (
            <div key={label} style={{ background: 'white', border: '1px solid var(--dd-border)', borderRadius: '10px', padding: '14px 16px', boxShadow: 'var(--dd-shadow)' }}>
              <div style={{ fontSize: '11px', color: '#9ca3af', textTransform: 'uppercase', letterSpacing: '0.06em', marginBottom: '6px' }}>{label}</div>
              <div style={{ fontSize: '16px', fontWeight: 700, color: red ? '#DC2626' : 'var(--dd-text)' }}>{value}</div>
            </div>
          ))}
        </div>
      ) : (
        <div style={{ background: 'white', border: '1px solid var(--dd-border)', borderRadius: '10px', padding: '16px 20px', marginBottom: '20px', color: 'var(--dd-text-muted)' }}>
          {est?.label ?? 'Requires deeper scoping — use the full scope flow.'}
        </div>
      )}

      {explain && (
        <>
          <div style={{ background: 'white', border: '1px solid var(--dd-border)', borderRadius: '10px', padding: '18px 20px', marginBottom: '12px', boxShadow: 'var(--dd-shadow)' }}>
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--dd-purple)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '8px' }}>
              Why this range
            </div>
            <p style={{ fontSize: '14px', color: 'var(--dd-text)', lineHeight: 1.6, margin: 0 }}>
              {explain.why}
            </p>
          </div>

          <div style={{ background: 'white', border: '1px solid var(--dd-border)', borderRadius: '10px', padding: '18px 20px', marginBottom: '24px', boxShadow: 'var(--dd-shadow)' }}>
            <div style={{ fontSize: '11px', fontWeight: 700, color: 'var(--dd-purple)', textTransform: 'uppercase', letterSpacing: '0.07em', marginBottom: '12px' }}>
              Next steps
            </div>
            <ol style={{ margin: 0, paddingLeft: '18px', display: 'flex', flexDirection: 'column', gap: '8px' }}>
              {explain.next_steps.map((step: string, i: number) => (
                <li key={i} style={{ fontSize: '14px', color: 'var(--dd-text)', lineHeight: 1.5 }}>{step}</li>
              ))}
            </ol>
          </div>
        </>
      )}

      <div style={{ display: 'flex', gap: '10px' }}>
        <button
          onClick={() => nav(`/estimate/${motion}`)}
          style={{ background: 'white', color: 'var(--dd-text)', border: '1px solid var(--dd-border)', borderRadius: '7px', padding: '9px 16px', fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}
        >
          ← Edit answers
        </button>
        <button
          onClick={() => {
            const products = ((answers.p1_products as string[]) || []).map(p => P1_TO_P2[p]).filter(Boolean)
            sessionStorage.setItem('p1_seed', JSON.stringify({
              motion,
              answers: {
                teamCount: answers.p1_teamCount,
                productScope: products.length ? products : undefined,
                urgency: answers.p1_deadline,
                migVol: answers.p1_migVol,
                _p1_stated_motion: motion,
              },
            }))
            nav('/scope')
          }}
          style={{ flex: 1, background: 'var(--dd-purple)', color: 'white', border: 'none', borderRadius: '7px', padding: '9px 16px', fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}
        >
          🔬 Refine with full scope →
        </button>
        <button
          onClick={() => { reset(); nav('/') }}
          style={{ background: 'transparent', color: 'var(--dd-text-muted)', border: 'none', borderRadius: '7px', padding: '9px 12px', fontSize: '13px', cursor: 'pointer' }}
        >
          Start over
        </button>
      </div>
    </div>
  )
}
