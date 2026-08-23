import { NavLink, Outlet, useNavigate } from 'react-router'

import { useAuth } from '../../lib/auth'
import { Button } from '../ui/Button'
import { Icon } from '../ui/Icon'

const navItems = [
  { to: '/admin/orders', label: 'Operations', icon: 'route' },
  { to: '/admin/agents', label: 'Agents', icon: 'user' },
  { to: '/admin/zones', label: 'Zones & Areas', icon: 'pin' },
  { to: '/admin/rates', label: 'Rate Cards', icon: 'list' },
  { to: '/admin/cod', label: 'COD Settings', icon: 'box' },
] as const

export function AdminShell() {
  const { logout, user } = useAuth()
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
            {navItems.map((item) => (
              <NavItem key={item.to} {...item} />
            ))}
          </nav>

          <div className="mt-auto border-t border-white/10 p-4">
            <div className="mb-4 flex items-center gap-3">
              <span className="flex h-10 w-10 items-center justify-center rounded-full bg-white/10 text-sm font-extrabold">
                {user?.name.slice(0, 1).toUpperCase() ?? 'A'}
              </span>
              <div className="min-w-0">
                <p className="truncate text-sm font-bold">{user?.name ?? 'Admin'}</p>
                <p className="truncate text-xs text-white/55">Admin</p>
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
          <NavLink className="flex items-center gap-2 font-extrabold" to="/admin/orders">
            <span className="flex h-9 w-9 items-center justify-center rounded-lg bg-[#071D34] text-[#F25F3A]">
              <Icon name="box" className="h-5 w-5" />
            </span>
            Operations
          </NavLink>
        </div>
        <nav className="mt-3 flex gap-2 overflow-x-auto pb-1 text-sm font-bold">
          {navItems.map((item) => (
            <NavLink
              key={item.to}
              className={({ isActive }) =>
                `shrink-0 rounded-md px-3 py-2 ${
                  isActive ? 'bg-white text-[#142033]' : 'text-[#667085]'
                }`
              }
              to={item.to}
            >
              {item.label}
            </NavLink>
          ))}
        </nav>
      </header>

      <main className="lg:pl-64">
        <Outlet />
      </main>
    </div>
  )
}

function NavItem({ to, label, icon }: (typeof navItems)[number]) {
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
