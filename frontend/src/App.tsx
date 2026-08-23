import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router'

import { AdminShell } from './components/layout/AdminShell'
import { AgentShell } from './components/layout/AgentShell'
import { CustomerShell } from './components/layout/CustomerShell'
import { AuthProvider, useAuth } from './lib/auth'
import AdminAgentsPage from './pages/admin/AdminAgentsPage'
import AdminCodPage from './pages/admin/AdminCodPage'
import AdminOrdersPage from './pages/admin/AdminOrdersPage'
import AdminRatesPage from './pages/admin/AdminRatesPage'
import AdminZonesPage from './pages/admin/AdminZonesPage'
import AgentOrdersPage from './pages/agent/AgentOrdersPage'
import AgentWorkspacePage from './pages/agent/AgentWorkspacePage'
import LoginPage from './pages/auth/LoginPage'
import RegisterPage from './pages/auth/RegisterPage'
import DashboardPage from './pages/customer/DashboardPage'
import NewOrderPage from './pages/customer/NewOrderPage'
import OrderDetailPage from './pages/customer/OrderDetailPage'
import OrdersPage from './pages/customer/OrdersPage'
import NotFoundPage from './pages/NotFoundPage'

function App() {
  return (
    <AuthProvider>
      <Routes>
        <Route path="/" element={<RoleRedirect />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route element={<RequireRole role="CUSTOMER" />}>
          <Route element={<CustomerShell />}>
            <Route path="/dashboard" element={<DashboardPage />} />
            <Route path="/orders" element={<OrdersPage />} />
            <Route path="/orders/new" element={<NewOrderPage />} />
            <Route path="/orders/:orderId" element={<OrderDetailPage />} />
            <Route
              path="/orders/:orderId/tracking"
              element={<OrderDetailPage trackingOnly />}
            />
          </Route>
        </Route>
        <Route element={<RequireRole role="ADMIN" />}>
          <Route element={<AdminShell />}>
            <Route path="/admin" element={<Navigate replace to="/admin/orders" />} />
            <Route path="/admin/orders" element={<AdminOrdersPage />} />
            <Route path="/admin/agents" element={<AdminAgentsPage />} />
            <Route path="/admin/zones" element={<AdminZonesPage />} />
            <Route path="/admin/rates" element={<AdminRatesPage />} />
            <Route path="/admin/cod" element={<AdminCodPage />} />
          </Route>
        </Route>
        <Route element={<RequireRole role="DELIVERY_AGENT" />}>
          <Route element={<AgentShell />}>
            <Route path="/agent" element={<AgentWorkspacePage />} />
            <Route path="/agent/orders" element={<AgentOrdersPage />} />
          </Route>
        </Route>
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AuthProvider>
  )
}

function RoleRedirect() {
  const { isLoading, user } = useAuth()

  if (isLoading) {
    return <LoadingScreen />
  }

  if (!user) {
    return <Navigate replace to="/login" />
  }

  if (user.role === 'ADMIN') return <Navigate replace to="/admin/orders" />
  if (user.role === 'DELIVERY_AGENT') return <Navigate replace to="/agent" />
  return <Navigate replace to="/dashboard" />
}

function RequireRole({ role }: { role: 'CUSTOMER' | 'DELIVERY_AGENT' | 'ADMIN' }) {
  const { isLoading, user } = useAuth()
  const location = useLocation()

  if (isLoading) {
    return <LoadingScreen />
  }

  if (!user) {
    return <Navigate replace state={{ from: location.pathname }} to="/login" />
  }

  if (user.role !== role) {
    return (
      <main className="grid min-h-screen place-items-center bg-[#F7F8F6] px-6 text-[#142033]">
        <div className="max-w-md rounded-2xl border border-[#DDE5E1] bg-white p-8 text-center">
          <p className="text-sm font-extrabold uppercase tracking-[0.12em] text-[#667085]">
            Protected workspace
          </p>
          <h1 className="mt-3 text-2xl font-extrabold">This area is not available for your role</h1>
          <p className="mt-3 text-sm font-semibold leading-6 text-[#667085]">
            Use the navigation for your assigned Last-Mile Delivery Tracker workspace.
          </p>
        </div>
      </main>
    )
  }

  return <Outlet />
}

function LoadingScreen() {
  return (
    <main className="grid min-h-screen place-items-center bg-[#F7F8F6] text-[#142033]">
      <div className="rounded-2xl border border-[#DDE5E1] bg-white p-6 text-center">
        <p className="text-sm font-extrabold uppercase tracking-[0.12em] text-[#667085]">
          Loading workspace
        </p>
        <p className="mt-2 text-lg font-extrabold">Preparing your delivery view</p>
      </div>
    </main>
  )
}

export default App
