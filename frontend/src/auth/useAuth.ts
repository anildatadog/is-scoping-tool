import { useState, useCallback } from 'react'

const TOKEN_KEY = 'goog_id_token'

export function useAuth() {
  const [token, setToken] = useState<string | null>(
    () => sessionStorage.getItem(TOKEN_KEY)
  )

  const login = useCallback((credential: string) => {
    sessionStorage.setItem(TOKEN_KEY, credential)
    setToken(credential)
  }, [])

  const logout = useCallback(() => {
    sessionStorage.removeItem(TOKEN_KEY)
    setToken(null)
  }, [])

  return { token, login, logout, isAuthenticated: !!token }
}
