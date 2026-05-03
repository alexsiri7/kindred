import { create } from 'zustand'
import type { Session } from '@supabase/supabase-js'

type AuthState = {
  session: Session | null
  initialized: boolean
  setSession: (s: Session | null) => void
  setInitialized: (v: boolean) => void
}

export const useAuth = create<AuthState>((set) => ({
  session: null,
  initialized: false,
  setSession: (session) => set({ session }),
  setInitialized: (initialized) => set({ initialized }),
}))
