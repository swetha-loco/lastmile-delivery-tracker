import { useEffect, useState } from 'react'
import { Link } from 'react-router'

import type { OrderPage } from '../../api/client'
import { ApiError, listAgentOrders } from '../../api/client'
import { RouteRail } from '../../components/orders/RouteRail'
import { StatusBadge } from '../../components/orders/StatusBadge'
import { Button } from '../../components/ui/Button'
import { Icon } from '../../components/ui/Icon'
import { useAuth } from '../../lib/auth'
import { formatCurrency, formatDateTime, orderCode } from '../../lib/format'

export default function AgentOrdersPage() {
  const { token } = useAuth()
  const [page, setPage] = useState<OrderPage | null>(null)
  const [pageNumber, setPageNumber] = useState(1)
  const [error, setError] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  useEffect(() => {
    if (!token) return
    setIsLoading(true)
    listAgentOrders(token, pageNumber, 10)
      .then((result) => {
        setPage(result)
        setError('')
      })
      .catch((exc: unknown) => {
        setError(exc instanceof ApiError ? exc.message : 'Unable to load assigned orders')
      })
      .finally(() => setIsLoading(false))
  }, [pageNumber, token])

  return (
    <div className="px-4 py-5 sm:px-6 lg:px-8 lg:py-8">
      <div className="mx-auto max-w-5xl">
        <div className="flex flex-wrap items-start justify-between gap-4">
          <div>
            <p className="text-xs font-extrabold uppercase tracking-[0.1em] text-[#667085]">
              Delivery queue
            </p>
            <h1 className="mt-1 text-3xl font-extrabold tracking-[-0.02em] text-[#071D34]">
              Assigned Orders
            </h1>
          </div>
          <Link
            className="inline-flex min-h-11 items-center justify-center rounded-lg border border-[#DDE5E1] bg-white px-4 text-sm font-bold text-[#142033] hover:bg-[#F7F8F6]"
            to="/agent"
          >
            Current delivery
          </Link>
        </div>

        {error ? (
          <p className="mt-5 rounded-lg border border-[#F1B5B5] bg-[#FDE7E7] p-4 text-sm font-bold text-[#B42318]">
            {error}
          </p>
        ) : null}

        <div className="mt-6 grid gap-4">
          {isLoading ? (
            <div className="h-72 animate-pulse rounded-2xl bg-white" />
          ) : page && page.items.length > 0 ? (
            page.items.map((order) => (
              <article key={order.id} className="rounded-2xl border border-[#DDE5E1] bg-white p-5">
                <div className="mb-4 flex flex-wrap items-center justify-between gap-3">
                  <div className="flex flex-wrap items-center gap-3">
                    <p className="font-mono text-lg font-extrabold text-[#071D34]">
                      {orderCode(order.id)}
                    </p>
                    <StatusBadge status={order.current_status} />
                  </div>
                  <p className="text-sm font-bold text-[#667085]">
                    {formatDateTime(order.created_at)}
                  </p>
                </div>
                <RouteRail
                  drop={order.drop_address}
                  dropZone={order.drop_zone_name}
                  pickup={order.pickup_address}
                  pickupZone={order.pickup_zone_name}
                />
                <div className="mt-4 flex flex-wrap items-center justify-between gap-3">
                  <p className="text-sm font-semibold text-[#667085]">
                    Collection total:{' '}
                    <span className="font-extrabold text-[#142033]">
                      {formatCurrency(order.total_charge)}
                    </span>
                  </p>
                  <Link
                    className="inline-flex min-h-10 items-center justify-center rounded-lg bg-[#071D34] px-4 text-sm font-bold text-white hover:bg-[#0B2947]"
                    to="/agent"
                  >
                    Open workspace
                  </Link>
                </div>
              </article>
            ))
          ) : (
            <section className="rounded-2xl border border-[#DDE5E1] bg-white p-8 text-center">
              <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[#DDF5EF] text-[#128C7E]">
                <Icon name="route" />
              </span>
              <h2 className="mt-4 text-2xl font-extrabold text-[#071D34]">
                No assigned orders
              </h2>
              <p className="mx-auto mt-2 max-w-md text-sm font-semibold leading-6 text-[#667085]">
                New assignments will appear here as soon as an admin assigns them to you.
              </p>
            </section>
          )}
        </div>

        {page && page.pages > 1 ? (
          <div className="mt-5 flex items-center justify-between rounded-xl border border-[#DDE5E1] bg-white p-3">
            <Button
              disabled={pageNumber <= 1}
              type="button"
              variant="secondary"
              onClick={() => setPageNumber((current) => Math.max(1, current - 1))}
            >
              Previous
            </Button>
            <p className="text-sm font-bold text-[#667085]">
              Page {page.page} of {page.pages}
            </p>
            <Button
              disabled={pageNumber >= page.pages}
              type="button"
              variant="secondary"
              onClick={() => setPageNumber((current) => current + 1)}
            >
              Next
            </Button>
          </div>
        ) : null}
      </div>
    </div>
  )
}
