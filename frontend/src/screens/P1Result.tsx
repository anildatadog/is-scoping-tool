import { useNavigate, useParams } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { useToken } from '../App'
import { useP1State } from '@/hooks/useP1State'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'
import { Badge } from '@/components/ui/badge'

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

  if (isLoading) return <p className="text-slate-500">Calculating…</p>
  const m = motions?.[motion]

  return (
    <div className="space-y-6">
      <div>
        <p className="text-xs text-slate-400 uppercase tracking-wide mb-1">Phase 1 estimate · first-pass only</p>
        <h1 className="text-2xl font-bold tracking-tight">{m?.label}</h1>
      </div>

      {est?.days_min != null ? (
        <div className="grid grid-cols-3 gap-4">
          {[
            { label: 'Recommended motion', value: m?.label },
            { label: 'Estimated days', value: `${est.days_min}–${est.days_max}` },
            { label: 'PM required?', value: <Badge variant={est.pm_required ? 'destructive' : 'secondary'}>{est.pm_required ? 'Yes' : 'No'}</Badge> },
          ].map(({ label, value }) => (
            <Card key={label}>
              <CardHeader><CardTitle className="text-sm text-slate-500">{label}</CardTitle></CardHeader>
              <CardContent className="font-semibold">{value}</CardContent>
            </Card>
          ))}
        </div>
      ) : (
        <Card><CardContent className="py-4 text-slate-600">{est?.label ?? 'Requires deeper scoping — use the full scope flow.'}</CardContent></Card>
      )}

      <div className="flex gap-3">
        <Button variant="outline" onClick={() => nav(`/estimate/${motion}`)}>← Edit answers</Button>
        <Button onClick={() => {
          const products = ((answers.p1_products as string[]) || []).map((p) => P1_TO_P2[p]).filter(Boolean)
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
        }}>
          🔬 Refine this estimate →
        </Button>
        <Button variant="ghost" onClick={() => { reset(); nav('/') }}>Start over</Button>
      </div>
    </div>
  )
}
