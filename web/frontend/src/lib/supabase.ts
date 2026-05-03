import { createClient } from '@supabase/supabase-js'
import { useAuth } from '../store/auth'

const url = import.meta.env.VITE_SUPABASE_URL ?? ''
const anon = import.meta.env.VITE_SUPABASE_ANON_KEY ?? ''

export const supabase = createClient(url, anon, {
  auth: {
    flowType: 'pkce',
    // AuthCallback page calls exchangeCodeForSession() explicitly. If
    // detectSessionInUrl were left on (the default), Supabase would race
    // our explicit call and one of them would fail with "code already
    // used" because PKCE codes are single-use.
    detectSessionInUrl: false,
  },
})

supabase.auth.onAuthStateChange((_event, session) => {
  const { setSession, setInitialized } = useAuth.getState()
  setSession(session)
  setInitialized(true)
})

void supabase.auth.getSession().then(({ data }) => {
  const { setSession, setInitialized } = useAuth.getState()
  setSession(data.session)
  setInitialized(true)
})
