import { Navigate, Outlet, Route, Routes, useLocation } from 'react-router'

import { CustomerShell } from './components/layout/CustomerShell'
import { AuthProvider, useAuth } from './lib/auth'
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
        <Route path="/" element={<Navigate replace to="/dashboard" />} />
        <Route path="/login" element={<LoginPage />} />
        <Route path="/register" element={<RegisterPage />} />
        <Route element={<RequireCustomer />}>
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
        <Route path="*" element={<NotFoundPage />} />
      </Routes>
    </AuthProvider>
  )
}

function RequireCustomer() {
  const { isLoading, user } = useAuth()
  const location = useLocation()

  if (isLoading) {
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

  if (!user) {
    return <Navigate replace state={{ from: location.pathname }} to="/login" />
  }

  if (user.role !== 'CUSTOMER') {
    return (
      <main className="grid min-h-screen place-items-center bg-[#F7F8F6] px-6 text-[#142033]">
        <div className="max-w-md rounded-2xl border border-[#DDE5E1] bg-white p-8 text-center">
          <p className="text-sm font-extrabold uppercase tracking-[0.12em] text-[#667085]">
            Customer workspace
          </p>
          <h1 className="mt-3 text-2xl font-extrabold">This area is for customers</h1>
          <p className="mt-3 text-sm font-semibold leading-6 text-[#667085]">
            Admin and delivery-agent screens will be added in later phases.
          </p>
        </div>
      </main>
    )
  }

  return <Outlet />
}

export default App
