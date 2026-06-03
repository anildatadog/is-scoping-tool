import { GoogleLogin } from '@react-oauth/google'

interface Props { onLogin: (credential: string) => void }

export function SignInScreen({ onLogin }: Props) {
  return (
    <div className="min-h-screen flex flex-col items-center justify-center gap-6 bg-slate-50">
      <div className="text-center space-y-2">
        <h1 className="text-3xl font-bold tracking-tight">🧭 IS Scoping Tool</h1>
        <p className="text-slate-500">Sign in with your Datadog Google account</p>
      </div>
      <GoogleLogin
        onSuccess={(r) => r.credential && onLogin(r.credential)}
        onError={() => console.error('Google login failed')}
        hosted_domain="datadoghq.com"
      />
    </div>
  )
}
