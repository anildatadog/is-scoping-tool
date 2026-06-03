import { Routes, Route, Navigate } from 'react-router-dom'
import { createContext, useContext } from 'react'
import { useAuth } from './auth/useAuth'
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

  if (!isAuthenticated) return <SignInScreen onLogin={login} />

  return (
    <AuthCtx.Provider value={{ token: token!, logout }}>
      <div className="min-h-screen bg-slate-50">
        <header className="border-b bg-white px-6 py-3 flex items-center justify-between">
          <span className="font-semibold text-slate-800">🧭 IS Scoping Tool</span>
          <button onClick={logout} className="text-sm text-slate-500 hover:text-slate-800">
            Sign out
          </button>
        </header>
        <main className="max-w-3xl mx-auto px-4 py-8">
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
