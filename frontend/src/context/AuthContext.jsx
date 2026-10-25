import { createContext, useContext, useEffect, useState, useCallback } from 'react'
import { api, getToken, setToken } from '../api/client'

const AuthCtx = createContext(null)
export const useAuth = () => useContext(AuthCtx)

export function AuthProvider({ children }) {
  const [user, setUser] = useState(null)
  const [loading, setLoading] = useState(!!getToken())

  useEffect(() => {
    if (!getToken()) return
    api.get('/auth/me').then((d) => setUser(d.user)).catch(() => setToken(null)).finally(() => setLoading(false))
  }, [])

  const login = useCallback(async (email, password) => {
    const d = await api.post('/auth/login', { email, password })
    setToken(d.token); setUser(d.user); return d.user
  }, [])
  const register = useCallback(async (form) => {
    const d = await api.post('/auth/register', form)
    setToken(d.token); setUser(d.user); return d.user
  }, [])
  const logout = useCallback(async () => {
    try { await api.post('/auth/logout') } catch { /* token may already be invalid */ }
    setToken(null); setUser(null)
  }, [])

  return <AuthCtx.Provider value={{ user, loading, login, register, logout }}>{children}</AuthCtx.Provider>
}

export const homeFor = (user) => (user?.role === 'admin' ? '/admin' : user?.role === 'coordinator' ? '/coordinator' : '/dashboard')
