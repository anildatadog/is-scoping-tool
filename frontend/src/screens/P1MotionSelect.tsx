import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { useToken } from '../App'
import { Card, CardContent } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export function P1MotionSelect() {
  const nav = useNavigate()
  const token = useToken()
  const { data: motions, isLoading } = useQuery({
    queryKey: ['phase1Motions'],
    queryFn: () => api.phase1Motions(token),
  })

  if (isLoading) return <p className="text-slate-500">Loading…</p>

  return (
    <div className="space-y-6">
      <div>
        <button onClick={() => nav('/')} className="text-sm text-slate-500 hover:text-slate-800 mb-4 block">← Back</button>
        <h1 className="text-2xl font-bold tracking-tight">What does the customer need?</h1>
        <p className="text-slate-500 mt-1">Pick the motion that best matches their ask. Not sure? Use the full scope flow.</p>
      </div>
      <div className="space-y-3">
        {motions && Object.entries(motions).map(([key, m]) => (
          <Card key={key} className="cursor-pointer hover:shadow-md transition-shadow">
            <CardContent className="p-4 flex items-center gap-4">
              <span className="text-2xl">{m.icon}</span>
              <div className="flex-1">
                <p className="font-semibold">{m.label}</p>
                <p className="text-sm text-slate-500">{m.ask}</p>
                <p className="text-xs text-slate-400 mt-1">{m.desc}</p>
              </div>
              <Button size="sm" onClick={() => nav(`/estimate/${key}`)}>Select</Button>
            </CardContent>
          </Card>
        ))}
      </div>
    </div>
  )
}
