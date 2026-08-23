import { NavLink, Outlet, useNavigate } from 'react-router'

import { useAuth } from '../../lib/auth'
import { Button } from '../ui/Button'
import { Icon } from '../ui/Icon'

export function AgentShell() {
  const { logout, user } = useAuth()
  const navigate = useNavigate()

  return (
    <div className="min-h-screen bg-[#F7F8F6] text-[#142033]">
      <aside className="fixed inset-y-0 left-0 z-20 hidden w-24 bg-[#071D34] text-white md:block">
        <div className="flex h-full flex-col items-center gap-4 py-5">
          <span className="flex h-11 w-11 items-center justify-center rounded-lg border border-white/15 text-[#F25F3A]">
            <Icon name="box" className="h-6 w-6" />
          </span>
          <nav className="grid gap-3">
            <AgentNav to="/agent" icon="box" label="Current" />
            <AgentNav to="/agent/orders" icon="list" label="Orders" />
          </nav>
          <div className="mt-auto">
            <button
              aria-label="Sign out"
              className="grid h-11 w-11 place-items-center rounded-lg text-white/70 hover:bg-white/10 hover:text-white"
              type="button"
              onClick={() => {
                logout()
                navigate('/login')
              }}
            >
              <Icon name="logOut" className="h-5 w-5" />
            </button>
          </div>
        </div>
      </aside>

      <header className="sticky top-0 z-10 border-b border-[#DDE5E1] bg-white/95 px-4 py-3 backdrop-blur md:hidden">
        <div className="flex items-center justify-between">
          <div>
            <p className="text-xs font-extrabold uppercase tracking-[0.12em] text-[#667085]">
              Delivery Agent
            </p>
            <p className="font-extrabold text-[#071D34]">{user?.name ?? 'Workspace'}</p>
          </div>
          <Button
            className="min-h-9 px-3"
            type="button"
            variant="secondary"
            onClick={() => navigate('/agent/orders')}
          >
            Orders
          </Button>
          <button
            aria-label="Sign out"
            className="grid h-10 w-10 place-items-center rounded-lg border border-[#DDE5E1] bg-white text-[#667085]"
            type="button"
            onClick={() => {
              logout()
              navigate('/login')
            }}
          >
            <Icon name="logOut" className="h-4 w-4" />
          </button>
        </div>
      </header>

      <main className="md:pl-24">
        <Outlet />
      </main>
    </div>
  )
}

function AgentNav({
  to,
  icon,
  label,
}: {
  to: string
  icon: 'box' | 'list'
  label: string
}) {
  return (
    <NavLink
      className={({ isActive }) =>
        `grid h-16 w-16 place-items-center rounded-xl text-xs font-bold transition ${
          isActive ? 'bg-white/10 text-[#F25F3A]' : 'text-white/70 hover:bg-white/5'
        }`
      }
      title={label}
      to={to}
    >
      <Icon name={icon} className="h-6 w-6" />
    </NavLink>
  )
}
