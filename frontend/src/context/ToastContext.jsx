import { createContext, useCallback, useContext, useState } from 'react'

const ToastCtx = createContext(null)
export const useToast = () => useContext(ToastCtx)

export function ToastProvider({ children }) {
  const [items, setItems] = useState([])
  const push = useCallback((message, type = 'success') => {
    const id = Math.random()
    setItems((x) => [...x, { id, message, type }])
    setTimeout(() => setItems((x) => x.filter((t) => t.id !== id)), 4500)
  }, [])
  const toast = { success: (m) => push(m, 'success'), error: (m) => push(m, 'error'), warn: (m) => push(m, 'warn') }
  return (
    <ToastCtx.Provider value={toast}>
      {children}
      <div className="toasts" role="status" aria-live="polite">
        {items.map((t) => <div key={t.id} className={`toast ${t.type}`}>{t.message}</div>)}
      </div>
    </ToastCtx.Provider>
  )
}
