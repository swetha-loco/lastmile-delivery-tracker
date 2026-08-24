import { Link } from 'react-router'

import { RouteRail } from '../components/orders/RouteRail'
import { Icon } from '../components/ui/Icon'
import { useAuth } from '../lib/auth'

function HomePage() {
  const { user } = useAuth()
  const workspacePath =
    user?.role === 'ADMIN'
      ? '/admin/orders'
      : user?.role === 'DELIVERY_AGENT'
        ? '/agent'
        : '/dashboard'

  return (
    <main className="min-h-screen bg-[#F7F8F6] text-[#142033]">
      <header className="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-5 sm:px-8 lg:px-10">
        <Link className="flex min-w-0 items-center gap-3" to="/">
          <span className="flex h-10 w-10 shrink-0 items-center justify-center rounded-xl bg-[#071D34] text-white">
            <Icon name="box" className="h-5 w-5" />
          </span>
          <span className="truncate text-base font-extrabold text-[#071D34]">
            Last-Mile Delivery Tracker
          </span>
        </Link>
        <nav className="flex shrink-0 items-center gap-2">
          <Link
            className="inline-flex min-h-10 items-center rounded-lg px-3 text-sm font-extrabold text-[#142033] hover:bg-white"
            to={user ? workspacePath : '/login'}
          >
            Sign in
          </Link>
          <Link
            className="inline-flex min-h-10 items-center rounded-lg bg-[#F25F3A] px-4 text-sm font-extrabold text-white hover:bg-[#E24E2E]"
            to={user ? workspacePath : '/register'}
          >
            Create delivery
          </Link>
        </nav>
      </header>

      <section className="mx-auto grid max-w-7xl gap-8 px-4 py-8 sm:px-8 lg:grid-cols-[minmax(0,1fr)_460px] lg:px-10 lg:py-16">
        <div className="max-w-3xl">
          <p className="text-sm font-extrabold uppercase tracking-[0.12em] text-[#667085]">
            Parcel operations, clearly tracked
          </p>
          <h1 className="mt-4 max-w-2xl text-5xl font-extrabold leading-[1.04] tracking-[-0.02em] text-[#071D34] sm:text-6xl">
            Deliver smarter. Track every step.
          </h1>
          <p className="mt-5 max-w-2xl text-lg font-semibold leading-8 text-[#667085]">
            Create deliveries with transparent pricing, assign agents through a focused
            operations flow, and keep customers updated with a complete tracking timeline.
          </p>
          <div className="mt-8 flex flex-wrap gap-3">
            <Link
              className="inline-flex min-h-12 items-center gap-2 rounded-lg bg-[#F25F3A] px-5 text-sm font-extrabold text-white hover:bg-[#E24E2E]"
              to={user ? workspacePath : '/register'}
            >
              <Icon name="plus" className="h-4 w-4" />
              Create a delivery
            </Link>
            <Link
              className="inline-flex min-h-12 items-center rounded-lg border border-[#DDE5E1] bg-white px-5 text-sm font-extrabold text-[#142033] hover:bg-[#F1F5F2]"
              to={user ? workspacePath : '/login'}
            >
              Sign in
            </Link>
          </div>
        </div>

        <div className="rounded-2xl border border-[#DDE5E1] bg-white p-5 shadow-sm">
          <div className="mb-5 flex items-center justify-between gap-4">
            <div>
              <p className="text-xs font-extrabold uppercase tracking-[0.1em] text-[#667085]">
                Delivery route
              </p>
              <p className="mt-1 font-mono text-xl font-extrabold text-[#071D34]">
                LM-00042
              </p>
            </div>
            <span className="rounded-md border border-[#BFE9DF] bg-[#DDF5EF] px-2.5 py-1 text-xs font-extrabold uppercase tracking-[0.04em] text-[#0F766E]">
              In transit
            </span>
          </div>
          <RouteRail
            drop="Adyar, Chennai 600020"
            dropZone="South"
            pickup="Mylapore, Chennai 600004"
            pickupZone="South"
            spacious
          />
          <div className="mt-5 grid grid-cols-4 gap-2">
            {['Created', 'Assigned', 'Picked up', 'In transit'].map((step, index) => (
              <div key={step} className="grid gap-2">
                <span
                  className={`h-1.5 rounded-full ${
                    index < 3 ? 'bg-[#128C7E]' : 'bg-[#F25F3A]'
                  }`}
                />
                <span className="text-xs font-bold text-[#667085]">{step}</span>
              </div>
            ))}
          </div>
        </div>
      </section>

      <section className="mx-auto max-w-7xl px-4 pb-14 sm:px-8 lg:px-10">
        <div className="grid gap-4 border-y border-[#DDE5E1] py-8 md:grid-cols-4">
          {[
            ['01', 'Enter pickup & drop'],
            ['02', 'Get an instant calculated quote'],
            ['03', 'A delivery agent is assigned'],
            ['04', 'Track every status update'],
          ].map(([number, label]) => (
            <div key={number} className="flex gap-3">
              <span className="font-mono text-sm font-extrabold text-[#F25F3A]">
                {number}
              </span>
              <span className="text-sm font-extrabold text-[#142033]">{label}</span>
            </div>
          ))}
        </div>

        <div className="mt-8 grid gap-4 md:grid-cols-3">
          <RoleCard
            title="Customer"
            body="Create deliveries, review pricing, and track progress."
          />
          <RoleCard
            title="Delivery Agent"
            body="Manage assigned deliveries and update status from the field."
          />
          <RoleCard
            title="Operations/Admin"
            body="Configure rates, zones, agents, and delivery assignments."
          />
        </div>
      </section>
    </main>
  )
}

function RoleCard({ title, body }: { title: string; body: string }) {
  return (
    <div className="rounded-xl border border-[#DDE5E1] bg-white p-5">
      <h2 className="font-extrabold text-[#071D34]">{title}</h2>
      <p className="mt-2 text-sm font-semibold leading-6 text-[#667085]">{body}</p>
    </div>
  )
}

export default HomePage
