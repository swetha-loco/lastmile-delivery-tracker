import { NavLink, Outlet, useNavigate } from 'react-router'

import { useAuth } from '../../lib/auth'
import { Button } from '../ui/Button'
import { Icon } from '../ui/Icon'

export function CustomerShell() {
  const { user, logout } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-[#F7F8F6] text-[#142033]">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-64 bg-[#071D34] text-white lg:block">
        <div className="flex h-full flex-col">
          <div className="flex items-center gap-3 border-b border-white/10 px-6 py-6">
            <span className="flex h-10 w-10 items-center justify-center rounded-lg border border-[#F25F3A]/50 text-[#F25F3A]">
              <Icon name="box" className="h-6 w-6" />
            </span>
            <div>
              <p className="text-sm font-extrabold leading-5">Last-Mile</p>
              <p className="text-sm font-extrabold leading-5">Delivery Tracker</p>
            </div>
          </div>

          <nav className="grid gap-2 px-3 py-5">
            <ShellLink to="/dashboard" icon="home" label="Dashboard" />
            <ShellLink to="/orders/new" icon="plus" label="Create delivery" />
            <ShellLink to="/orders" icon="list" label="Orders" />
          </nav>

          <div className="mt-auto border-t border-white/10 p-4">
            <div className="mb-4 flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-sm font-extrabold">
                {user?.name.slice(0, 1).toUpperCase() ?? 'C'}
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm font-bold">{user?.name ?? 'Customer'}</p>
                <p className="truncate text-xs text-white/55">{user?.email}</p>
              </div>
            </div>
            <Button
              className="w-full !bg-white/5 !text-white hover:!bg-white/10"
              type="button"
              variant="ghost"
              onClick={() => {
                logout()
                navigate('/login')
              }}
            >
              <Icon name="logOut" className="h-4 w-4" />
              Sign out
            </Button>
          </div>
        </div>
      </aside>

      <header className="sticky top-0 z-10 border-b border-[#DDE5E1] bg-[#F7F8F6]/95 px-4 py-3 backdrop-blur lg:hidden">
        <div className="flex items-center justify-between">
          <NavLink className="flex items-center gap-2 font-extrabold" to="/dashboard">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#071D34] text-[#F25F3A]">
              <Icon name="box" className="h-5 w-5" />
            </span>
            Last-Mile
          </NavLink>
          <Button
            className="min-h-9 px-3"
            type="button"
            variant="secondary"
            onClick={() => navigate('/orders/new')}
          >
            <Icon name="plus" className="h-4 w-4" />
            Create
          </Button>
        </div>
        <nav className="mt-3 grid grid-cols-3 gap-2 text-center text-sm font-bold">
          <MobileLink to="/dashboard" label="Dashboard" />
          <MobileLink to="/orders/new" label="Create" />
          <MobileLink to="/orders" label="Orders" />
        </nav>
      </header>

      <main className="lg:pl-64">
        <Outlet />
      </main>
    </div>
  )
}

function ShellLink({
  to,
  icon,
  label,
}: {
  to: string
  icon: 'home' | 'plus' | 'list'
  label: string
}) {
  return (
    <NavLink
      className={({ isActive }) =>
        `flex items-center gap-3 rounded-lg px-4 py-3 text-sm font-bold transition ${
          isActive
            ? 'bg-white/10 text-white'
            : 'text-white/70 hover:bg-white/5 hover:text-white'
        }`
      }
      to={to}
    >
      <Icon name={icon} className="h-5 w-5" />
      {label}
    </NavLink>
  )
}

function MobileLink({ to, label }: { to: string; label: string }) {
  return (
    <NavLink
      className={({ isActive }) =>
        `rounded-md px-2 py-2 ${isActive ? 'bg-white text-[#142033]' : 'text-[#667085]'}`
      }
      to={to}
    >
      {label}
    </NavLink>
  )
}
