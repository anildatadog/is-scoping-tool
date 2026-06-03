import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { useToken } from '../App'
import { useP1State } from '@/hooks/useP1State'

type Opt = { v: string; l: string }
type Q = { id: string; q: string; kind: string; opts: Opt[]; show: () => boolean }

function getQuestions(motion: string): Q[] {
  const all: Q[] = [
    { id: 'p1_teamCount', q: 'How many teams or workstreams are in scope?', kind: 'radio', show: () => true,
      opts: [{ v: 'single', l: '1 team' }, { v: 'multi', l: '2–5 teams' }, { v: 'enterprise', l: '6–15 teams' }, { v: 'large', l: '15+ teams or multiple business units' }] },
    { id: 'p1_products', q: 'Which product categories are in scope?', kind: 'multiselect', show: () => true,
      opts: [{ v: 'obs', l: 'Standard observability (Infra, APM, Logs)' }, { v: 'dx', l: 'Digital Experience (RUM, Synthetics)' }, { v: 'security', l: 'Cloud Security (CSPM, ASM, SIEM)' }, { v: 'ai', l: 'AI / LLM Observability' }, { v: 'finops', l: 'FinOps / Cloud Cost Management' }] },
    { id: 'p1_readiness', q: 'How ready is their environment?', kind: 'radio', show: () => motion !== 'discovery',
      opts: [{ v: 'ready', l: 'Ready — telemetry flowing, owners named' }, { v: 'partial', l: 'Partial — some instrumentation exists' }, { v: 'missing', l: 'Starting from zero' }] },
    { id: 'p1_migVol', q: 'Roughly how many dashboards / alert rules exist in the tool being replaced?', kind: 'radio', show: () => motion === 'migration',
      opts: [{ v: 's', l: 'Under 50' }, { v: 'm', l: '50–200' }, { v: 'l', l: '200–500' }, { v: 'xl', l: '500+' }, { v: 'unk', l: 'Unknown yet' }] },
    { id: 'p1_deadline', q: 'Is there a hard external deadline?', kind: 'radio', show: () => motion !== 'discovery',
      opts: [{ v: 'hard', l: 'Yes — within 3 months' }, { v: 'target', l: 'Target date (flexible)' }, { v: 'flex', l: 'No hard deadline' }] },
  ]
  return all.filter(q => q.show())
}

function OptionRow({ selected, onClick, children }: { selected: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: '12px',
        padding: '11px 14px',
        borderRadius: '8px',
        border: `1px solid ${selected ? 'var(--dd-purple)' : 'var(--dd-border)'}`,
        background: selected ? 'var(--dd-purple-light)' : 'white',
        cursor: 'pointer',
        transition: 'all 0.1s ease',
        userSelect: 'none',
      }}
    >
      <div style={{
        width: '16px', height: '16px', borderRadius: '50%', flexShrink: 0,
        border: `2px solid ${selected ? 'var(--dd-purple)' : '#d1d5db'}`,
        background: selected ? 'var(--dd-purple)' : 'white',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {selected && <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'white' }} />}
      </div>
      <span style={{ fontSize: '14px', color: selected ? 'var(--dd-purple-dark)' : 'var(--dd-text)', fontWeight: selected ? 500 : 400 }}>
        {children}
      </span>
    </div>
  )
}

function CheckRow({ selected, onClick, children }: { selected: boolean; onClick: () => void; children: React.ReactNode }) {
  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'center', gap: '12px',
        padding: '10px 14px',
        borderRadius: '8px',
        border: `1px solid ${selected ? 'var(--dd-purple)' : 'var(--dd-border)'}`,
        background: selected ? 'var(--dd-purple-light)' : 'white',
        cursor: 'pointer',
        transition: 'all 0.1s ease',
        userSelect: 'none',
      }}
    >
      <div style={{
        width: '16px', height: '16px', borderRadius: '4px', flexShrink: 0,
        border: `2px solid ${selected ? 'var(--dd-purple)' : '#d1d5db'}`,
        background: selected ? 'var(--dd-purple)' : 'white',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {selected && (
          <svg width="10" height="8" viewBox="0 0 10 8" fill="none">
            <path d="M1 4L3.5 6.5L9 1" stroke="white" strokeWidth="1.8" strokeLinecap="round" strokeLinejoin="round"/>
          </svg>
        )}
      </div>
      <span style={{ fontSize: '14px', color: selected ? 'var(--dd-purple-dark)' : 'var(--dd-text)', fontWeight: selected ? 500 : 400 }}>
        {children}
      </span>
    </div>
  )
}

export function P1Questionnaire() {
  const { motion = '' } = useParams()
  const nav = useNavigate()
  const token = useToken()
  const { answers, setAnswer } = useP1State()
  const { data: motions } = useQuery({ queryKey: ['phase1Motions'], queryFn: () => api.phase1Motions(token) })

  const questions = getQuestions(motion)
  const allAnswered = questions.every(q => q.kind === 'multiselect' ? true : !!answers[q.id])

  return (
    <div>
      <button
        onClick={() => nav('/estimate')}
        style={{
          background: 'transparent', border: 'none', cursor: 'pointer',
          color: 'var(--dd-text-muted)', fontSize: '13px', padding: '0 0 16px 0',
          display: 'flex', alignItems: 'center', gap: '4px', fontWeight: 500,
        }}
      >
        ← Change motion
      </button>

      <div style={{ marginBottom: '28px' }}>
        <h1 style={{ fontSize: '22px', fontWeight: 700, margin: '0 0 4px 0', letterSpacing: '-0.3px' }}>
          {motions?.[motion]?.label ?? motion}
        </h1>
        <p style={{ color: 'var(--dd-text-muted)', fontSize: '14px', margin: 0 }}>
          Answer these questions to get a rough day range.
        </p>
      </div>

      <div style={{ display: 'flex', flexDirection: 'column', gap: '20px' }}>
        {questions.map(q => (
          <div key={q.id} style={{ background: 'white', border: '1px solid var(--dd-border)', borderRadius: '10px', padding: '18px 20px', boxShadow: 'var(--dd-shadow)' }}>
            <div style={{ fontSize: '14px', fontWeight: 600, color: 'var(--dd-text)', marginBottom: '12px' }}>
              {q.q}
            </div>
            <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
              {q.opts.map(o => {
                const isMulti = q.kind === 'multiselect'
                const curr = (answers[q.id] as string[] | string | undefined)
                const selected = isMulti
                  ? ((curr as string[]) || []).includes(o.v)
                  : curr === o.v

                if (isMulti) {
                  return (
                    <CheckRow
                      key={o.v}
                      selected={selected}
                      onClick={() => {
                        const list = (curr as string[]) || []
                        setAnswer(q.id, selected ? list.filter(x => x !== o.v) : [...list, o.v])
                      }}
                    >
                      {o.l}
                    </CheckRow>
                  )
                }
                return (
                  <OptionRow key={o.v} selected={selected} onClick={() => setAnswer(q.id, o.v)}>
                    {o.l}
                  </OptionRow>
                )
              })}
            </div>
          </div>
        ))}
      </div>

      <div style={{ marginTop: '24px' }}>
        <button
          disabled={!allAnswered}
          onClick={() => nav(`/estimate/${motion}/result`)}
          style={{
            width: '100%',
            background: allAnswered ? 'var(--dd-purple)' : '#e5e7eb',
            color: allAnswered ? 'white' : '#9ca3af',
            border: 'none',
            borderRadius: '8px',
            padding: '12px',
            fontSize: '14px',
            fontWeight: 600,
            cursor: allAnswered ? 'pointer' : 'not-allowed',
            transition: 'background 0.15s ease',
            boxShadow: allAnswered ? '0 1px 3px rgba(99,44,166,0.25)' : 'none',
          }}
        >
          Get estimate →
        </button>
      </div>
    </div>
  )
}
