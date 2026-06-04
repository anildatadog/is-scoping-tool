import { Routes, Route, Navigate } from 'react-router-dom'
import { createContext, useContext, useEffect } from 'react'
import { useQueryClient } from '@tanstack/react-query'
import { useAuth } from './auth/useAuth'
import { ApiError } from './api/client'
import ddLogo from './assets/dd_logo_h_rgb.svg'
import { SignInScreen } from './screens/SignInScreen'
import { HomeScreen } from './screens/HomeScreen'
import { P1MotionSelect } from './screens/P1MotionSelect'
import { P1Questionnaire } from './screens/P1Questionnaire'
import { P1Result } from './screens/P1Result'
import { SearchScreen } from './screens/SearchScreen'
import { ReviewScreen } from './screens/ReviewScreen'
import { QuestionnaireScreen } from './screens/QuestionnaireScreen'
import { ResultScreen } from './screens/ResultScreen'

export const AuthCtx = createContext<{ token: string; logout: () => void }>({
  token: '', logout: () => {},
})
export const useToken = () => useContext(AuthCtx).token

export default function App() {
  const { token, login, logout, isAuthenticated } = useAuth()
  const qc = useQueryClient()

  // Any 401 from any API call means the Google session expired — sign out silently
  useEffect(() => {
    const unsubscribe = qc.getQueryCache().subscribe(event => {
      if (event.type === 'updated' && event.query.state.status === 'error') {
        const err = event.query.state.error
        if (err instanceof ApiError && err.status === 401) {
          logout()
        }
      }
    })
    return unsubscribe
  }, [qc, logout])

  if (!isAuthenticated) return <SignInScreen onLogin={login} />

  return (
    <AuthCtx.Provider value={{ token: token!, logout }}>
      <div style={{ minHeight: '100vh', background: 'var(--dd-bg)' }}>
        <header style={{
          background: 'white',
          borderBottom: '1px solid var(--dd-border)',
          padding: '0 24px',
          height: '52px',
          display: 'flex',
          alignItems: 'center',
          justifyContent: 'space-between',
          position: 'sticky',
          top: 0,
          zIndex: 50,
          boxShadow: '0 1px 0 var(--dd-border)',
        }}>
          <div style={{ display: 'flex', alignItems: 'center', gap: '12px' }}>
            <img src={ddLogo} alt="Datadog" style={{ height: '22px', width: 'auto' }} />
            <div style={{
              width: '1px', height: '18px',
              background: 'var(--dd-border)',
            }} />
            <span style={{ fontSize: '13px', fontWeight: 600, color: '#374151', letterSpacing: '-0.01em' }}>
              IS Scoping
            </span>
          </div>
          <button
            onClick={logout}
            style={{
              background: 'transparent',
              border: '1px solid var(--dd-border)',
              borderRadius: '6px',
              padding: '5px 12px',
              fontSize: '12px',
              color: '#6b7280',
              cursor: 'pointer',
              fontWeight: 500,
            }}
          >
            Sign out
          </button>
        </header>
        <main style={{ maxWidth: '820px', margin: '0 auto', padding: '32px 24px' }}>
          <Routes>
            <Route path="/" element={<HomeScreen />} />
            <Route path="/estimate" element={<P1MotionSelect />} />
            <Route path="/estimate/:motion" element={<P1Questionnaire />} />
            <Route path="/estimate/:motion/result" element={<P1Result />} />
            <Route path="/scope" element={<SearchScreen />} />
            <Route path="/scope/review" element={<ReviewScreen />} />
            <Route path="/scope/questions" element={<QuestionnaireScreen />} />
            <Route path="/scope/result" element={<ResultScreen />} />
            <Route path="*" element={<Navigate to="/" replace />} />
          </Routes>
        </main>
      </div>
    </AuthCtx.Provider>
  )
}
