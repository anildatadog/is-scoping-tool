import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { useToken } from '../App'
import { useP1State } from '@/hooks/useP1State'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Checkbox } from '@/components/ui/checkbox'

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
  return all.filter((q) => q.show())
}

export function P1Questionnaire() {
  const { motion = '' } = useParams()
  const nav = useNavigate()
  const token = useToken()
  const { answers, setAnswer } = useP1State()

  const { data: motions } = useQuery({ queryKey: ['phase1Motions'], queryFn: () => api.phase1Motions(token) })
  const questions = getQuestions(motion)
  const allAnswered = questions.every((q) => q.kind === 'multiselect' ? true : !!answers[q.id])

  return (
    <div className="space-y-8">
      <div>
        <button onClick={() => nav('/estimate')} className="text-sm text-slate-500 hover:text-slate-800 mb-4 block">← Change motion</button>
        <h1 className="text-2xl font-bold tracking-tight">{motions?.[motion]?.label ?? motion}</h1>
        <p className="text-slate-500 mt-1">Answer these questions to get a rough day range.</p>
      </div>

      {questions.map((q) => (
        <div key={q.id} className="space-y-3">
          <Label className="text-base font-medium">{q.q}</Label>
          {q.kind === 'multiselect' ? (
            <div className="space-y-2">
              {q.opts.map((o) => (
                <div key={o.v} className="flex items-center gap-2">
                  <Checkbox
                    id={`${q.id}-${o.v}`}
                    checked={((answers[q.id] as string[]) || []).includes(o.v)}
                    onCheckedChange={(checked) => {
                      const curr = (answers[q.id] as string[]) || []
                      setAnswer(q.id, checked ? [...curr, o.v] : curr.filter((x) => x !== o.v))
                    }}
                  />
                  <Label htmlFor={`${q.id}-${o.v}`} className="font-normal cursor-pointer">{o.l}</Label>
                </div>
              ))}
            </div>
          ) : (
            <RadioGroup value={(answers[q.id] as string) || ''} onValueChange={(v) => setAnswer(q.id, v)} className="space-y-2">
              {q.opts.map((o) => (
                <div key={o.v} className="flex items-center gap-2">
                  <RadioGroupItem value={o.v} id={`${q.id}-${o.v}`} />
                  <Label htmlFor={`${q.id}-${o.v}`} className="font-normal cursor-pointer">{o.l}</Label>
                </div>
              ))}
            </RadioGroup>
          )}
        </div>
      ))}

      <Button disabled={!allAnswered} onClick={() => nav(`/estimate/${motion}/result`)} className="w-full">
        Get estimate →
      </Button>
    </div>
  )
}
