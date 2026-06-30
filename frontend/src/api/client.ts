import type {
  AccountResult, SfData,
  DiagnoseRequest, DiagnoseResponse,
  GovernedHandoffRequest, GovernedHandoffResponse,
  ProseRequest, ProseResponse,
  MotionsResponse, EstimateRequest, EstimateResponse,
} from '@/api-types'

const BASE = import.meta.env.VITE_BACKEND_URL ?? 'https://is-scoping-backend-151745717948.us-central1.run.app'

export class ApiError extends Error {
  status: number
  constructor(status: number, message: string) {
    super(message)
    this.status = status
  }
}

async function req<T>(method: string, path: string, token: string, body?: unknown): Promise<T> {
  let r: Response
  try {
    r = await fetch(`${BASE}${path}`, {
      method,
      headers: { 'Content-Type': 'application/json', 'Authorization': `Bearer ${token}` },
      body: body ? JSON.stringify(body) : undefined,
    })
  } catch {
    throw new ApiError(0, 'network')
  }
  if (!r.ok) throw new ApiError(r.status, `${r.status}`)
  return r.json()
}

export const api = {
  search: (q: string, token: string) =>
    req<(AccountResult | SfData)[]>('GET', `/search?q=${encodeURIComponent(q)}`, token),

  selectAccount: (account: AccountResult, token: string) =>
    req<SfData>('POST', '/accounts/select', token, { account }),

  lookup: (oppId: string, token: string) =>
    req<SfData>('GET', `/lookup?opp_id=${encodeURIComponent(oppId)}`, token),

  diagnose: (body: DiagnoseRequest, token: string) =>
    req<DiagnoseResponse>('POST', '/diagnose', token, body),

  prose: (body: ProseRequest, token: string) =>
    req<ProseResponse>('POST', '/prose', token, body),

  phase1Motions: (token: string) =>
    req<MotionsResponse>('GET', '/phase1/motions', token),

  phase1Estimate: (body: EstimateRequest, token: string) =>
    req<EstimateResponse>('POST', '/phase1/estimate', token, body),

  phase1Explain: (body: EstimateRequest, token: string) =>
    req<{ why: string; next_steps: string[] }>('POST', '/phase1/explain', token, body),

  governedHandoff: (body: GovernedHandoffRequest, token: string) =>
    req<GovernedHandoffResponse>('POST', '/scoping/governed_handoff', token, body),
}
