import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useP2State } from '@/hooks/useP2State'
import { QUESTIONS } from '@/data/questions'

function OptionRow({ selected, onClick, label, sublabel }: {
  selected: boolean; onClick: () => void; label: string; sublabel?: string
}) {
  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'flex-start', gap: '12px',
        padding: '11px 14px', borderRadius: '8px', cursor: 'pointer',
        border: `1px solid ${selected ? 'var(--dd-purple)' : 'var(--dd-border)'}`,
        background: selected ? 'var(--dd-purple-light)' : 'white',
        transition: 'all 0.1s ease', userSelect: 'none',
      }}
    >
      <div style={{
        width: '16px', height: '16px', borderRadius: '50%', flexShrink: 0, marginTop: '2px',
        border: `2px solid ${selected ? 'var(--dd-purple)' : '#d1d5db'}`,
        background: selected ? 'var(--dd-purple)' : 'white',
        display: 'flex', alignItems: 'center', justifyContent: 'center',
      }}>
        {selected && <div style={{ width: '6px', height: '6px', borderRadius: '50%', background: 'white' }} />}
      </div>
      <div>
        <div style={{ fontSize: '14px', color: selected ? 'var(--dd-purple-dark)' : 'var(--dd-text)', fontWeight: selected ? 500 : 400 }}>
          {label}
        </div>
        {sublabel && <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '2px' }}>{sublabel}</div>}
      </div>
    </div>
  )
}

function CheckRow({ selected, onClick, label, sublabel }: {
  selected: boolean; onClick: () => void; label: string; sublabel?: string
}) {
  return (
    <div
      onClick={onClick}
      style={{
        display: 'flex', alignItems: 'flex-start', gap: '12px',
        padding: '10px 14px', borderRadius: '8px', cursor: 'pointer',
        border: `1px solid ${selected ? 'var(--dd-purple)' : 'var(--dd-border)'}`,
        background: selected ? 'var(--dd-purple-light)' : 'white',
        transition: 'all 0.1s ease', userSelect: 'none',
      }}
    >
      <div style={{
        width: '16px', height: '16px', borderRadius: '4px', flexShrink: 0, marginTop: '2px',
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
      <div>
        <div style={{ fontSize: '14px', color: selected ? 'var(--dd-purple-dark)' : 'var(--dd-text)', fontWeight: selected ? 500 : 400 }}>
          {label}
        </div>
        {sublabel && <div style={{ fontSize: '12px', color: '#9ca3af', marginTop: '2px' }}>{sublabel}</div>}
      </div>
    </div>
  )
}

export function QuestionnaireScreen() {
  const nav = useNavigate()
  const { answers, setAnswer } = useP2State()
  const [step, setStep] = useState(0)

  const visible = QUESTIONS.filter(q => q.show(answers))
  const q = visible[step]
  const pct = Math.round((step / visible.length) * 100)

  if (!q) { nav('/scope/result'); return null }

  const hasAnswer = q.kind === 'multiselect' ? true : !!answers[q.id]

  function next() {
    if (step < visible.length - 1) setStep(step + 1)
    else nav('/scope/result')
  }

  return (
    <div>
      <div style={{ marginBottom: '24px' }}>
        <div style={{ display: 'flex', justifyContent: 'space-between', marginBottom: '8px' }}>
          <span style={{ fontSize: '13px', color: 'var(--dd-text-muted)', fontWeight: 500 }}>
            Question {step + 1} of {visible.length}
          </span>
          <span style={{ fontSize: '13px', color: 'var(--dd-purple)', fontWeight: 600 }}>{pct}%</span>
        </div>
        <div style={{ height: '4px', background: '#e5e7eb', borderRadius: '2px', overflow: 'hidden' }}>
          <div style={{ height: '100%', background: 'var(--dd-purple)', borderRadius: '2px', width: `${pct}%`, transition: 'width 0.3s ease' }} />
        </div>
      </div>

      <div style={{ background: 'white', border: '1px solid var(--dd-border)', borderRadius: '10px', padding: '20px', boxShadow: 'var(--dd-shadow)', marginBottom: '16px' }}>
        <div style={{ fontSize: '15px', fontWeight: 600, color: 'var(--dd-text)', marginBottom: '14px' }}>{q.q}</div>
        <div style={{ display: 'flex', flexDirection: 'column', gap: '6px' }}>
          {q.opts.map((o: any) => {
            const isMulti = q.kind === 'multiselect'
            const curr = answers[q.id]
            const selected = isMulti ? ((curr as string[]) || []).includes(o.v) : curr === o.v
            if (isMulti) {
              return (
                <CheckRow key={o.v} selected={selected} label={o.l} sublabel={o.s}
                  onClick={() => {
                    const list = (curr as string[]) || []
                    setAnswer(q.id, selected ? list.filter((x: string) => x !== o.v) : [...list, o.v])
                  }} />
              )
            }
            return <OptionRow key={o.v} selected={selected} label={o.l} sublabel={o.s} onClick={() => setAnswer(q.id, o.v)} />
          })}
        </div>
      </div>

      <div style={{ display: 'flex', gap: '10px' }}>
        {step > 0 && (
          <button onClick={() => setStep(step - 1)}
            style={{ background: 'white', color: 'var(--dd-text)', border: '1px solid var(--dd-border)', borderRadius: '7px', padding: '10px 20px', fontSize: '13px', fontWeight: 600, cursor: 'pointer' }}>
            ← Back
          </button>
        )}
        <button onClick={next} disabled={!hasAnswer}
          style={{
            flex: 1, border: 'none', borderRadius: '7px', padding: '10px', fontSize: '13px', fontWeight: 600,
            background: hasAnswer ? 'var(--dd-purple)' : '#e5e7eb',
            color: hasAnswer ? 'white' : '#9ca3af',
            cursor: hasAnswer ? 'pointer' : 'not-allowed',
            transition: 'background 0.15s ease',
          }}>
          {step < visible.length - 1 ? 'Next →' : 'See results →'}
        </button>
      </div>
    </div>
  )
}
