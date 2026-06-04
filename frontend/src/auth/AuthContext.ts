import { createContext, useContext } from 'react'

export const AuthCtx = createContext<{ token: string; logout: () => void }>({
  token: '',
  logout: () => {},
})

export const useToken = () => useContext(AuthCtx).token
