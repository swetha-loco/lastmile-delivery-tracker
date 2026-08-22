import {
  createContext,
  useCallback,
  useContext,
  useEffect,
  useMemo,
  useState,
  type ReactNode,
} from 'react'

import { getMe, login as loginRequest, type User } from '../api/client'

const TOKEN_KEY = 'lastmile.customer.token'

type AuthContextValue = {
  token: string | null
  user: User | null
  isLoading: boolean
  login: (email: string, password: string) => Promise<void>
  logout: () => void
  refreshUser: () => Promise<void>
}

const AuthContext = createContext<AuthContextValue | null>(null)

export function AuthProvider({ children }: { children: ReactNode }) {
  const [token, setToken] = useState<string | null>(() =>
    window.localStorage.getItem(TOKEN_KEY),
  )
  const [user, setUser] = useState<User | null>(null)
  const [isLoading, setIsLoading] = useState(true)

  const logout = useCallback(() => {
    window.localStorage.removeItem(TOKEN_KEY)
    setToken(null)
    setUser(null)
  }, [])

  const refreshUser = useCallback(async () => {
    if (!token) {
      setUser(null)
      setIsLoading(false)
      return
    }

    try {
      setUser(await getMe(token))
    } catch {
      logout()
    } finally {
      setIsLoading(false)
    }
  }, [logout, token])

  useEffect(() => {
    void refreshUser()
  }, [refreshUser])

  const login = useCallback(async (email: string, password: string) => {
    const response = await loginRequest(email, password)
    window.localStorage.setItem(TOKEN_KEY, response.access_token)
    setToken(response.access_token)
    setUser(await getMe(response.access_token))
  }, [])

  const value = useMemo(
    () => ({ token, user, isLoading, login, logout, refreshUser }),
    [isLoading, login, logout, refreshUser, token, user],
  )

  return <AuthContext.Provider value={value}>{children}</AuthContext.Provider>
}

export function useAuth() {
  const context = useContext(AuthContext)
  if (!context) {
    throw new Error('useAuth must be used inside AuthProvider')
  }
  return context
}
