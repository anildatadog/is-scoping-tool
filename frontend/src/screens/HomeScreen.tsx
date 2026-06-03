import { useNavigate } from 'react-router-dom'
import { Card, CardContent, CardDescription, CardHeader, CardTitle } from '@/components/ui/card'
import { Button } from '@/components/ui/button'

export function HomeScreen() {
  const nav = useNavigate()
  return (
    <div className="space-y-6">
      <div>
        <h1 className="text-2xl font-bold tracking-tight">IS Scoping Tool</h1>
        <p className="text-slate-500 mt-1">Size an Implementation Services engagement</p>
      </div>
      <div className="grid grid-cols-2 gap-4">
        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => nav('/estimate')}>
          <CardHeader>
            <CardTitle className="text-lg">⚡ Quick estimate</CardTitle>
            <CardDescription>Pick a motion, answer 3–5 questions, get a rough day range in under 2 minutes.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button className="w-full">Start quick estimate →</Button>
          </CardContent>
        </Card>
        <Card className="cursor-pointer hover:shadow-md transition-shadow" onClick={() => nav('/scope')}>
          <CardHeader>
            <CardTitle className="text-lg">🔍 Full scope</CardTitle>
            <CardDescription>Look up an opportunity in Salesforce, answer diagnostic questions, get a full diagnosis.</CardDescription>
          </CardHeader>
          <CardContent>
            <Button variant="outline" className="w-full">Look up opportunity →</Button>
          </CardContent>
        </Card>
      </div>
    </div>
  )
}
