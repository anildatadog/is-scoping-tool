import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useP2State } from '@/hooks/useP2State'
import { Button } from '@/components/ui/button'
import { Label } from '@/components/ui/label'
import { RadioGroup, RadioGroupItem } from '@/components/ui/radio-group'
import { Checkbox } from '@/components/ui/checkbox'
import { Progress } from '@/components/ui/progress'
import { QUESTIONS } from '@/data/questions'

export function QuestionnaireScreen() {
  const nav = useNavigate()
  const { answers, setAnswer } = useP2State()
  const [step, setStep] = useState(0)

  const visible = QUESTIONS.filter((q) => q.show(answers))
  const q = visible[step]
  const pct = Math.round((step / visible.length) * 100)

  if (!q) { nav('/scope/result'); return null }

  const hasAnswer = q.kind === 'multiselect' ? true : !!answers[q.id]

  function next() {
    if (step < visible.length - 1) setStep(step + 1)
    else nav('/scope/result')
  }

  return (
    <div className="space-y-6">
      <div>
        <div className="flex items-center justify-between mb-2">
          <span className="text-sm text-slate-500">Question {step + 1} of {visible.length}</span>
          <span className="text-sm text-slate-500">{pct}%</span>
        </div>
        <Progress value={pct} className="h-1" />
      </div>

      <div className="space-y-4">
        <Label className="text-lg font-medium">{q.q}</Label>

        {q.kind === 'multiselect' ? (
          <div className="space-y-2">
            {q.opts.map((o) => (
              <div key={o.v} className="flex items-start gap-3">
                <Checkbox
                  id={`${q.id}-${o.v}`}
                  checked={((answers[q.id] as string[]) || []).includes(o.v)}
                  onCheckedChange={(checked) => {
                    const curr = (answers[q.id] as string[]) || []
                    setAnswer(q.id, checked ? [...curr, o.v] : curr.filter((x) => x !== o.v))
                  }}
                />
                <div>
                  <Label htmlFor={`${q.id}-${o.v}`} className="font-normal cursor-pointer">{o.l}</Label>
                  {o.s && <p className="text-xs text-slate-400">{o.s}</p>}
                </div>
              </div>
            ))}
          </div>
        ) : (
          <RadioGroup value={(answers[q.id] as string) || ''} onValueChange={(v) => setAnswer(q.id, v)} className="space-y-3">
            {q.opts.map((o) => (
              <div key={o.v} className="flex items-start gap-3">
                <RadioGroupItem value={o.v} id={`${q.id}-${o.v}`} className="mt-0.5" />
                <div>
                  <Label htmlFor={`${q.id}-${o.v}`} className="font-normal cursor-pointer">{o.l}</Label>
                  {o.s && <p className="text-xs text-slate-400">{o.s}</p>}
                </div>
              </div>
            ))}
          </RadioGroup>
        )}
      </div>

      <div className="flex gap-3">
        {step > 0 && <Button variant="outline" onClick={() => setStep(step - 1)}>← Back</Button>}
        <Button onClick={next} disabled={!hasAnswer} className="flex-1">
          {step < visible.length - 1 ? 'Next →' : 'See results →'}
        </Button>
      </div>
    </div>
  )
}
