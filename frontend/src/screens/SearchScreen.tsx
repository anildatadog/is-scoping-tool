import { useState } from 'react'
import { useNavigate } from 'react-router-dom'
import { useQuery } from '@tanstack/react-query'
import { api } from '@/api/client'
import { useToken } from '../App'
import { useP2State } from '@/hooks/useP2State'
import { Input } from '@/components/ui/input'
import { Button } from '@/components/ui/button'
import { Card, CardContent } from '@/components/ui/card'
import type { AccountResult, SfData } from '@shared/api-types'

export function SearchScreen() {
  const [q, setQ] = useState('')
  const [submitted, setSubmitted] = useState('')
  const nav = useNavigate()
  const token = useToken()
  const { setSfData } = useP2State()

  const { data: results, isLoading, error } = useQuery({
    queryKey: ['search', submitted],
    queryFn: () => api.search(submitted, token),
    enabled: submitted.length > 0,
  })

  function select(item: AccountResult | SfData) {
    if ('prefill' in item) {
      setSfData(item as SfData)
      nav('/scope/review')
    } else {
      api.selectAccount(item as AccountResult, token).then((sfData) => {
        setSfData(sfData)
        nav('/scope/review')
      })
    }
  }

  function skip() {
    const seed = sessionStorage.getItem('p1_seed')
    const p1 = seed ? JSON.parse(seed) : null
    setSfData({ accountName: '', prefill: p1 ? { ...p1.answers, _p1_stated_motion: p1.motion } : {} })
    nav('/scope/review')
  }

  return (
    <div className="space-y-6">
      <div>
        <button onClick={() => nav('/')} className="text-sm text-slate-500 hover:text-slate-800 mb-4 block">← Back</button>
        <h1 className="text-2xl font-bold tracking-tight">Find this opportunity</h1>
        <p className="text-slate-500 mt-1">Search by account name or paste an opp ID (006…)</p>
      </div>

      <div className="flex gap-2">
        <Input
          placeholder="Acme Corp or 006Qx…"
          value={q}
          onChange={(e) => setQ(e.target.value)}
          onKeyDown={(e) => e.key === 'Enter' && setSubmitted(q)}
        />
        <Button onClick={() => setSubmitted(q)} disabled={!q}>Search</Button>
      </div>

      {isLoading && <p className="text-slate-500">Searching…</p>}
      {error && <p className="text-red-500 text-sm">Search failed — try again</p>}
      {results && results.length === 0 && <p className="text-slate-500 text-sm">No results for "{submitted}"</p>}

      {results && results.length > 0 && (
        <div className="space-y-2">
          {(results as Array<AccountResult | SfData>).map((item, i) => {
            const name = 'ACCOUNT_NAME' in item ? (item as AccountResult).ACCOUNT_NAME : (item as SfData).accountName
            const sub = 'SALES_SEGMENT' in item ? (item as AccountResult).SALES_SEGMENT : undefined
            return (
              <Card key={i} className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => select(item)}>
                <CardContent className="p-4 flex items-center justify-between">
                  <div>
                    <p className="font-medium">{name}</p>
                    {sub && <p className="text-sm text-slate-500">{sub}</p>}
                  </div>
                  <Button size="sm" variant="outline">Select →</Button>
                </CardContent>
              </Card>
            )
          })}
        </div>
      )}

      <Button variant="ghost" onClick={skip} className="text-slate-500">
        Skip Salesforce lookup — answer questions manually
      </Button>
    </div>
  )
}
