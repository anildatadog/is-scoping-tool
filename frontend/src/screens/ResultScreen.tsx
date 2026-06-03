import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { useToken } from '../App'
import { useP2State } from '@/hooks/useP2State'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'
import { Button } from '@/components/ui/button'
import { Separator } from '@/components/ui/separator'

const FLAG_VARIANT: Record<string, 'destructive' | 'secondary'> = { blk: 'destructive', wrn: 'destructive', inf: 'secondary', ok: 'secondary' }

export function ResultScreen() {
  const nav = useNavigate()
  const token = useToken()
  const { sfData, answers, reset } = useP2State()

  const { data: diag, isLoading: diagLoading } = useQuery({
    queryKey: ['diagnose', answers],
    queryFn: () => api.diagnose({ answers }, token),
    enabled: Object.keys(answers).length > 0,
  })

  const { data: prose, isLoading: proseLoading } = useQuery({
    queryKey: ['prose', diag],
    queryFn: () => api.prose({ diagnosis: diag!.diagnosis, answers }, token),
    enabled: !!diag,
  })

  if (diagLoading) return <p className="text-slate-500">Running diagnosis…</p>
  if (!diag) return <p className="text-red-500">No answers — <button onClick={() => nav('/scope')} className="underline">start over</button></p>

  const isDefer = diag.diagnosis.shape.value === 'Defer'

  return (
    <div className="space-y-6">
      <div className="flex items-start justify-between">
        <div>
          <p className="text-xs text-slate-400 uppercase tracking-wide">{sfData?.accountName || 'Manual entry'}</p>
          <h1 className="text-2xl font-bold tracking-tight mt-1">{diag.service_motion}</h1>
        </div>
        <Badge variant="outline">{diag.diagnosis.shape.value}</Badge>
      </div>

      {proseLoading && <p className="text-slate-500 text-sm italic">Writing diagnosis…</p>}

      {prose?.diagnosis_paragraph && (
        <Card>
          <CardContent className="py-4 space-y-3 text-sm leading-relaxed">
            <p><strong>Diagnosis.</strong> {prose.diagnosis_paragraph}</p>
            <p><strong>Consequence.</strong> {prose.consequence_paragraph}</p>
          </CardContent>
        </Card>
      )}

      {!isDefer && (
        <>
          {diag.recommendation.sMax != null && (
            <Card>
              <CardHeader><CardTitle className="text-sm">Commercial</CardTitle></CardHeader>
              <CardContent className="space-y-1 text-sm">
                <p>Sessions: <strong>{diag.recommendation.sMin}–{diag.recommendation.sMax}</strong></p>
                <p>Indicative value: <strong>${((diag.recommendation.sMin ?? 0) * 1700).toLocaleString()} – ${(diag.recommendation.sMax * 1700).toLocaleString()}</strong></p>
              </CardContent>
            </Card>
          )}

          {diag.flags.length > 0 && (
            <div className="space-y-2">
              {diag.flags.map((f: { t: string; m: string }, i: number) => (
                <div key={i} className="flex items-start gap-2">
                  <Badge variant={FLAG_VARIANT[f.t] ?? 'secondary'} className="mt-0.5 shrink-0">{f.t.toUpperCase()}</Badge>
                  <p className="text-sm">{f.m}</p>
                </div>
              ))}
            </div>
          )}

          {diag.diagnosis.customer_ownership.length > 0 && (
            <Card>
              <CardHeader><CardTitle className="text-sm">Customer owns</CardTitle></CardHeader>
              <CardContent>
                <ul className="space-y-1">
                  {diag.diagnosis.customer_ownership.map((b: string, i: number) => (
                    <li key={i} className="text-sm flex gap-2"><span>·</span><span>{b}</span></li>
                  ))}
                </ul>
              </CardContent>
            </Card>
          )}
        </>
      )}

      <Separator />
      <div className="flex gap-3">
        <Button variant="outline" onClick={() => nav('/scope/questions')}>← Edit answers</Button>
        <Button variant="ghost" onClick={() => { reset(); nav('/') }}>Start over</Button>
      </div>
    </div>
  )
}
