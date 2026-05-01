import { Link, Navigate, Outlet, useLocation } from 'react-router'
import { useAuth } from '../store/auth'
import { supabase } from '../lib/supabase'

export function Layout() {
  const session = useAuth((s) => s.session)
  const location = useLocation()

  if (!session && location.pathname !== '/login') {
    return <Navigate to="/login" replace />
  }

  if (location.pathname === '/login') {
    return <Outlet />
  }

  return (
    <div className="min-h-screen bg-stone-50 text-stone-900">
      <nav className="border-b border-stone-200 bg-white">
        <div className="mx-auto flex max-w-3xl items-center gap-6 px-6 py-4 text-sm">
          <Link to="/" className="font-semibold">
            Kindred
          </Link>
          <Link to="/patterns">Patterns</Link>
          <Link to="/search">Search</Link>
          <Link to="/connect">Connect</Link>
          <Link to="/settings" className="ml-auto">
            Settings
          </Link>
          <button
            type="button"
            onClick={() => void supabase.auth.signOut()}
            className="text-stone-500 hover:text-stone-900"
          >
            Sign out
          </button>
        </div>
      </nav>
      <main className="mx-auto max-w-3xl px-6 py-8">
        <Outlet />
      </main>
    </div>
  )
}
