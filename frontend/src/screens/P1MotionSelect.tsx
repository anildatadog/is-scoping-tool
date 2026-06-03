import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { useToken } from '../App'
import type { Motion } from '@/api-types'

const MOTION_ICONS: Record<string, string> = {
  consultative: '💬', onboarding: '🤝', hok: '⌨️',
  migration: '🔄', resident_architect: '🏗️', discovery: '🔍',
}

export function P1MotionSelect() {
  const nav = useNavigate()
  const token = useToken()
  const { data: motions, isLoading, error } = useQuery({
    queryKey: ['phase1Motions'],
    queryFn: () => api.phase1Motions(token),
  })

  return (
    <div>
      <button
        onClick={() => nav('/')}
        style={{
          background: 'transparent', border: 'none', cursor: 'pointer',
          color: 'var(--dd-text-muted)', fontSize: '13px', padding: '0 0 16px 0',
          display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 500,
        }}
      >
        ← Back
      </button>

      <div style={{ marginBottom: '24px' }}>
        <h1 style={{ fontSize: '22px', fontWeight: 700, margin: 0, letterSpacing: '-0.3px' }}>
          What does the customer need?
        </h1>
        <p style={{ color: 'var(--dd-text-muted)', fontSize: '14px', marginTop: '6px' }}>
          Pick the motion that best matches their ask. Not sure? Use the full scope flow.
        </p>
      </div>

      {isLoading && <p style={{ color: 'var(--dd-text-muted)', fontSize: '14px' }}>Loading…</p>}
      {error && (
        <div style={{ background: '#FEF2F2', border: '1px solid #FECACA', borderRadius: '8px', padding: '12px 16px', color: '#DC2626', fontSize: '13px' }}>
          Failed to load — is the backend running?
        </div>
      )}

      {motions && (
        <div style={{ display: 'flex', flexDirection: 'column', gap: '8px' }}>
          {(Object.entries(motions) as [string, Motion][]).map(([key, m]) => (
            <div
              key={key}
              onClick={() => nav(`/estimate/${key}`)}
              style={{
                background: 'white',
                border: '1px solid var(--dd-border)',
                borderRadius: '10px',
                padding: '16px 20px',
                cursor: 'pointer',
                display: 'grid',
                gridTemplateColumns: '44px 1fr',
                alignItems: 'center',
                gap: '16px',
                boxShadow: 'var(--dd-shadow)',
                transition: 'border-color 0.12s ease, box-shadow 0.12s ease',
              }}
              onMouseEnter={e => {
                const el = e.currentTarget as HTMLElement
                el.style.borderColor = '#C4A8E8'
                el.style.boxShadow = '0 0 0 3px rgba(99,44,166,0.07), var(--dd-shadow)'
              }}
              onMouseLeave={e => {
                const el = e.currentTarget as HTMLElement
                el.style.borderColor = 'var(--dd-border)'
                el.style.boxShadow = 'var(--dd-shadow)'
              }}
            >
              <div style={{
                width: '40px', height: '40px',
                background: 'var(--dd-purple-light)',
                borderRadius: '8px',
                display: 'flex', alignItems: 'center', justifyContent: 'center',
                fontSize: '18px', flexShrink: 0,
              }}>
                {MOTION_ICONS[key] ?? '🔹'}
              </div>
              <div>
                <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--dd-text)', marginBottom: '2px' }}>
                  {m.label}
                </div>
                <div style={{ fontSize: '12px', color: '#9ca3af', fontStyle: 'italic', marginBottom: '3px' }}>
                  {m.ask}
                </div>
                <div style={{ fontSize: '12px', color: 'var(--dd-text-muted)', lineHeight: 1.4 }}>
                  {m.desc}
                </div>
              </div>
            </div>
          ))}
        </div>
      )}
    </div>
  )
}
