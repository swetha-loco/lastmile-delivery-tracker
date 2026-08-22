import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router'

import type { OrderPage, TrackingResponse } from '../../api/client'
import { ApiError, getTracking, listOrders } from '../../api/client'
import { OrderRow } from '../../components/orders/OrderRow'
import { RouteRail } from '../../components/orders/RouteRail'
import { StatusBadge } from '../../components/orders/StatusBadge'
import { Icon } from '../../components/ui/Icon'
import { useAuth } from '../../lib/auth'
import { formatCurrency, formatDateTime, orderCode, statusLabel } from '../../lib/format'

export default function DashboardPage() {
  const { token, user } = useAuth()
  const [orders, setOrders] = useState<OrderPage | null>(null)
  const [tracking, setTracking] = useState<TrackingResponse | null>(null)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!token) return

    let isCurrent = true
    setIsLoading(true)
    listOrders(token, 1, 5)
      .then(async (page) => {
        if (!isCurrent) return
        setOrders(page)
        const active =
          page.items.find((order) => order.current_status !== 'DELIVERED') ?? page.items[0]
        if (active) {
          setTracking(await getTracking(token, String(active.id)))
        }
      })
      .catch((exc) => {
        if (isCurrent) {
          setError(exc instanceof ApiError ? exc.message : 'Unable to load orders')
        }
      })
      .finally(() => {
        if (isCurrent) setIsLoading(false)
      })

    return () => {
      isCurrent = false
    }
  }, [token])

  const activeOrder = useMemo(
    () => orders?.items.find((order) => order.current_status !== 'DELIVERED') ?? orders?.items[0],
    [orders],
  )

  return (
    <div className="px-4 py-6 sm:px-8 lg:px-10 lg:py-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-8 flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-sm font-extrabold uppercase tracking-[0.12em] text-[#667085]">
              Customer workspace
            </p>
            <h1 className="mt-2 text-3xl font-extrabold tracking-[-0.02em] text-[#071D34] sm:text-4xl">
              Hello, {user?.name?.split(' ')[0] ?? 'there'}
            </h1>
          </div>
          <Link
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[#F25F3A] px-4 text-sm font-bold text-white shadow-[0_10px_24px_rgba(242,95,58,0.20)] transition hover:bg-[#E24E2E] active:translate-y-px"
            to="/orders/new"
          >
            <Icon name="plus" className="h-4 w-4" />
            Create delivery
          </Link>
        </div>

        {error ? <Alert message={error} /> : null}

        {isLoading ? (
          <DashboardSkeleton />
        ) : activeOrder ? (
          <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
            <section className="rounded-2xl border border-[#DDE5E1] bg-white p-5 shadow-[0_18px_50px_rgba(7,29,52,0.06)] sm:p-6">
              <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
                <div>
                  <p className="font-mono text-sm font-extrabold text-[#667085]">
                    {orderCode(activeOrder.id)}
                  </p>
                  <h2 className="mt-1 text-2xl font-extrabold text-[#142033]">
                    Current shipment
                  </h2>
                </div>
                <StatusBadge status={activeOrder.current_status} />
              </div>

              <RouteRail
                drop={activeOrder.drop_address}
                dropZone={activeOrder.drop_zone_name}
                pickup={activeOrder.pickup_address}
                pickupZone={activeOrder.pickup_zone_name}
                spacious
              />

              <div className="mt-6 grid gap-4 md:grid-cols-3">
                <MiniFact label="Status" value={statusLabel(activeOrder.current_status)} />
                <MiniFact label="Total charge" value={formatCurrency(activeOrder.total_charge)} />
                <MiniFact
                  label="Assigned agent"
                  value={
                    activeOrder.current_agent_id
                      ? `Agent #${activeOrder.current_agent_id}`
                      : 'Awaiting assignment'
                  }
                />
              </div>

              <div className="mt-6 flex flex-wrap gap-3">
                <Link
                  className="inline-flex min-h-11 items-center justify-center rounded-lg border border-[#DDE5E1] bg-white px-4 text-sm font-bold text-[#142033] transition hover:bg-[#F7F8F6]"
                  to={`/orders/${activeOrder.id}`}
                >
                  View details
                </Link>
                <Link
                  className="inline-flex min-h-11 items-center justify-center rounded-lg border border-[#DDE5E1] bg-white px-4 text-sm font-bold text-[#142033] transition hover:bg-[#F7F8F6]"
                  to={`/orders/${activeOrder.id}/tracking`}
                >
                  Tracking timeline
                </Link>
              </div>
            </section>

            <aside className="rounded-2xl border border-[#DDE5E1] bg-white p-5">
              <p className="text-xs font-extrabold uppercase tracking-[0.1em] text-[#667085]">
                Latest progress
              </p>
              <div className="mt-5 grid gap-4">
                {tracking?.history.slice(-4).reverse().map((entry) => (
                  <div key={entry.id} className="flex gap-3">
                    <span className="mt-1 h-3 w-3 rounded-full bg-[#128C7E]" />
                    <div>
                      <p className="font-extrabold text-[#142033]">
                        {statusLabel(entry.to_status)}
                      </p>
                      <p className="text-sm font-semibold text-[#667085]">
                        {formatDateTime(entry.created_at)}
                      </p>
                    </div>
                  </div>
                ))}
                {!tracking?.history.length ? (
                  <p className="text-sm font-semibold text-[#667085]">
                    Timeline appears after your order is confirmed.
                  </p>
                ) : null}
              </div>
            </aside>
          </div>
        ) : (
          <EmptyOrders />
        )}

        <section className="mt-8 rounded-2xl border border-[#DDE5E1] bg-white">
          <div className="flex items-center justify-between border-b border-[#DDE5E1] px-5 py-4">
            <h2 className="text-lg font-extrabold text-[#142033]">Recent orders</h2>
            <Link className="text-sm font-extrabold text-[#F25F3A]" to="/orders">
              View all
            </Link>
          </div>
          {orders?.items.length ? (
            orders.items.map((order) => <OrderRow key={order.id} order={order} />)
          ) : (
            <p className="p-5 text-sm font-semibold text-[#667085]">
              Your recent deliveries will appear here.
            </p>
          )}
        </section>
      </div>
    </div>
  )
}

function MiniFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-[#F7F8F6] p-4">
      <p className="text-xs font-extrabold uppercase tracking-[0.08em] text-[#667085]">
        {label}
      </p>
      <p className="mt-2 font-extrabold text-[#142033]">{value}</p>
    </div>
  )
}

function Alert({ message }: { message: string }) {
  return (
    <p className="mb-5 rounded-lg border border-[#F1B5B5] bg-[#FDE7E7] p-4 text-sm font-bold text-[#B42318]">
      {message}
    </p>
  )
}

function DashboardSkeleton() {
  return (
    <div className="grid gap-6 xl:grid-cols-[1fr_360px]">
      <div className="h-80 animate-pulse rounded-2xl bg-white" />
      <div className="h-80 animate-pulse rounded-2xl bg-white" />
    </div>
  )
}

function EmptyOrders() {
  return (
    <section className="rounded-2xl border border-dashed border-[#C9D6D1] bg-white p-8 text-center">
      <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-xl bg-[#DDF5EF] text-[#128C7E]">
        <Icon name="box" className="h-7 w-7" />
      </div>
      <h2 className="mt-5 text-2xl font-extrabold text-[#142033]">No deliveries yet</h2>
      <p className="mx-auto mt-2 max-w-md text-sm font-semibold leading-6 text-[#667085]">
        Create your first delivery to receive a quote, confirm the price, and track
        every status change.
      </p>
      <Link
        className="mt-6 inline-flex min-h-11 items-center justify-center rounded-lg bg-[#F25F3A] px-4 text-sm font-bold text-white hover:bg-[#E24E2E]"
        to="/orders/new"
      >
        Create delivery
      </Link>
    </section>
  )
}
