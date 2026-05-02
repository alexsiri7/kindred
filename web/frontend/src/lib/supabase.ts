import { createClient } from '@supabase/supabase-js'
import { useAuth } from '../store/auth'

const url = import.meta.env.VITE_SUPABASE_URL ?? ''
const anon = import.meta.env.VITE_SUPABASE_ANON_KEY ?? ''

export const supabase = createClient(url, anon, {
  auth: { flowType: 'pkce' },
})

supabase.auth.onAuthStateChange((_event, session) => {
  useAuth.getState().setSession(session)
})

void supabase.auth.getSession().then(({ data }) => {
  useAuth.getState().setSession(data.session)
})
