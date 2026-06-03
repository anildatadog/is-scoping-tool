import { useNavigate } from 'react-router-dom'
import { useP2State } from '@/hooks/useP2State'
import { Button } from '@/components/ui/button'
import { Card, CardContent, CardHeader, CardTitle } from '@/components/ui/card'
import { Badge } from '@/components/ui/badge'

export function ReviewScreen() {
  const nav = useNavigate()
  const { sfData, answers } = useP2State()

  if (!sfData) { nav('/scope'); return null }

  const prefillKeys = Object.keys(sfData.prefill || {}).filter((k) => !k.startsWith('_'))

  return (
    <div className="space-y-6">
      <div>
        <button onClick={() => nav('/scope')} className="text-sm text-slate-500 hover:text-slate-800 mb-4 block">← Search again</button>
        <h1 className="text-2xl font-bold tracking-tight">{sfData.accountName || 'Manual entry'}</h1>
        <p className="text-slate-500 mt-1">Review Salesforce data, then continue to questions</p>
      </div>

      {sfData.accountFamilyMRR != null && (
        <p className="text-slate-600 text-sm">Account MRR: <strong>${sfData.accountFamilyMRR.toLocaleString()}</strong></p>
      )}

      {sfData.ddProducts && sfData.ddProducts.length > 0 && (
        <div>
          <p className="text-sm text-slate-500 mb-2">Contracted products</p>
          <div className="flex flex-wrap gap-2">
            {sfData.ddProducts.map((p) => <Badge key={p} variant="secondary">{p}</Badge>)}
          </div>
        </div>
      )}

      {prefillKeys.length > 0 && (
        <Card>
          <CardHeader><CardTitle className="text-sm">Pre-filled from Salesforce</CardTitle></CardHeader>
          <CardContent className="space-y-1">
            {prefillKeys.map((k) => (
              <p key={k} className="text-sm">
                <span className="text-slate-500">{k}:</span>{' '}
                <span className="font-medium">{String(answers[k] ?? sfData.prefill[k])}</span>
              </p>
            ))}
          </CardContent>
        </Card>
      )}

      <Button onClick={() => nav('/scope/questions')} className="w-full">Continue to questions →</Button>
    </div>
  )
}
