import { createContext, useContext, useEffect, useState, type ReactNode } from 'react'
import { api } from '../api'
import type { User } from '../types'

interface UserContextValue {
  users: User[]
  current: User | null
  setCurrent: (u: User) => void
}

const UserContext = createContext<UserContextValue>({
  users: [],
  current: null,
  setCurrent: () => {},
})

export function UserProvider({ children }: { children: ReactNode }) {
  const [users, setUsers] = useState<User[]>([])
  const [current, setCurrentState] = useState<User | null>(null)

  useEffect(() => {
    api.users().then((us) => {
      setUsers(us)
      const saved = localStorage.getItem('bpv-user')
      const found = us.find((u) => u.key === saved)
      setCurrentState(found ?? us[0] ?? null)
    })
  }, [])

  const setCurrent = (u: User) => {
    setCurrentState(u)
    localStorage.setItem('bpv-user', u.key)
  }

  return (
    <UserContext.Provider value={{ users, current, setCurrent }}>
      {children}
    </UserContext.Provider>
  )
}

export function useUser() {
  const ctx = useContext(UserContext)
  return { ...ctx, userKey: ctx.current?.key ?? 'tanaka' }
}
