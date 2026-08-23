import { useEffect, useState } from 'react'
import { Link } from 'react-router'

import type { OrderPage } from '../../api/client'
import { ApiError, listOrders } from '../../api/client'
import { OrderRow } from '../../components/orders/OrderRow'
import { Button } from '../../components/ui/Button'
import { Icon } from '../../components/ui/Icon'
import { useAuth } from '../../lib/auth'

export default function OrdersPage() {
  const { token } = useAuth()
  const [page, setPage] = useState(1)
  const [orders, setOrders] = useState<OrderPage | null>(null)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!token) return
    let isCurrent = true
    setIsLoading(true)
    listOrders(token, page, 10)
      .then((response) => {
        if (isCurrent) {
          setOrders(response)
          setError('')
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
  }, [page, token])

  return (
    <div className="px-4 py-6 sm:px-8 lg:px-10 lg:py-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-7 flex flex-wrap items-end justify-between gap-4">
          <div>
            <p className="text-sm font-extrabold uppercase tracking-[0.12em] text-[#667085]">
              Order history
            </p>
            <h1 className="mt-2 text-3xl font-extrabold tracking-[-0.02em] text-[#071D34]">
              Your deliveries
            </h1>
          </div>
          <Link
            className="inline-flex min-h-11 items-center justify-center gap-2 rounded-lg bg-[#F25F3A] px-4 text-sm font-bold text-white hover:bg-[#E24E2E]"
            to="/orders/new"
          >
            <Icon name="plus" className="h-4 w-4" />
            Create delivery
          </Link>
        </div>

        {error ? (
          <p className="mb-5 rounded-lg border border-[#F1B5B5] bg-[#FDE7E7] p-4 text-sm font-bold text-[#B42318]">
            {error}
          </p>
        ) : null}

        <section className="overflow-hidden rounded-2xl border border-[#DDE5E1] bg-white">
          <div className="hidden border-b border-[#DDE5E1] bg-[#F7F8F6] px-4 py-3 text-xs font-extrabold uppercase tracking-[0.08em] text-[#667085] md:grid md:grid-cols-[120px_minmax(0,1fr)_max-content_minmax(92px,120px)_max-content] md:items-center">
            <span>Order</span>
            <span>Route</span>
            <span>Status</span>
            <span>Agent</span>
            <span className="justify-self-end">Amount</span>
          </div>

          {isLoading ? (
            <div className="grid gap-2 p-4">
              {Array.from({ length: 5 }).map((_, index) => (
                <div key={index} className="h-16 animate-pulse rounded-lg bg-[#F1F5F2]" />
              ))}
            </div>
          ) : orders?.items.length ? (
            orders.items.map((order) => <OrderRow key={order.id} order={order} />)
          ) : (
            <div className="p-10 text-center">
              <div className="mx-auto flex h-14 w-14 items-center justify-center rounded-xl bg-[#DDF5EF] text-[#128C7E]">
                <Icon name="route" className="h-7 w-7" />
              </div>
              <h2 className="mt-5 text-xl font-extrabold text-[#142033]">No orders yet</h2>
              <p className="mt-2 text-sm font-semibold text-[#667085]">
                Confirm a quote to start your delivery timeline.
              </p>
            </div>
          )}
        </section>

        {orders && orders.pages > 1 ? (
          <div className="mt-5 flex items-center justify-between">
            <p className="text-sm font-semibold text-[#667085]">
              Page {orders.page} of {orders.pages}
            </p>
            <div className="flex gap-2">
              <Button
                disabled={page <= 1}
                type="button"
                variant="secondary"
                onClick={() => setPage((current) => Math.max(1, current - 1))}
              >
                Previous
              </Button>
              <Button
                disabled={page >= orders.pages}
                type="button"
                variant="secondary"
                onClick={() => setPage((current) => current + 1)}
              >
                Next
              </Button>
            </div>
          </div>
        ) : null}
      </div>
    </div>
  )
}
