import { useEffect, useState } from 'react'
import { Link, useLocation, useParams } from 'react-router'

import type { OrderDetail, TrackingResponse } from '../../api/client'
import { ApiError, getOrder, getTracking, rescheduleOrder } from '../../api/client'
import { PriceBreakdown } from '../../components/orders/PriceBreakdown'
import { RouteRail } from '../../components/orders/RouteRail'
import { StatusBadge } from '../../components/orders/StatusBadge'
import { TrackingTimeline } from '../../components/orders/TrackingTimeline'
import { Button } from '../../components/ui/Button'
import { FormField, TextInput } from '../../components/ui/FormField'
import { Icon } from '../../components/ui/Icon'
import { useAuth } from '../../lib/auth'
import {
  formatCurrency,
  formatDateTime,
  orderCode,
  statusLabel,
  tomorrowDateValue,
} from '../../lib/format'

export default function OrderDetailPage({ trackingOnly = false }: { trackingOnly?: boolean }) {
  const { orderId } = useParams()
  const { token } = useAuth()
  const location = useLocation()
  const [order, setOrder] = useState<OrderDetail | null>(null)
  const [tracking, setTracking] = useState<TrackingResponse | null>(null)
  const [scheduledDate, setScheduledDate] = useState(tomorrowDateValue)
  const [error, setError] = useState('')
  const [flash, setFlash] = useState(
    (location.state as { flash?: string } | null)?.flash ?? '',
  )
  const [isLoading, setIsLoading] = useState(true)
  const [isRescheduling, setIsRescheduling] = useState(false)

  async function loadOrder() {
    if (!token || !orderId) return
    setIsLoading(true)
    try {
      const [detail, timeline] = await Promise.all([
        getOrder(token, orderId),
        getTracking(token, orderId),
      ])
      setOrder(detail)
      setTracking(timeline)
      setError('')
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to load order')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void loadOrder()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [orderId, token])

  async function handleReschedule(event: React.FormEvent) {
    event.preventDefault()
    if (!token || !orderId) return
    setIsRescheduling(true)
    setError('')
    setFlash('')
    try {
      await rescheduleOrder(token, orderId, scheduledDate)
      setFlash('Delivery rescheduled. A new attempt is waiting for assignment.')
      await loadOrder()
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to reschedule delivery')
    } finally {
      setIsRescheduling(false)
    }
  }

  return (
    <div className="px-4 py-6 sm:px-8 lg:px-10 lg:py-8">
      <div className="mx-auto max-w-7xl">
        {isLoading ? (
          <div className="h-[560px] animate-pulse rounded-2xl bg-white" />
        ) : order ? (
          <>
            <div className="mb-7 flex flex-wrap items-start justify-between gap-4">
              <div>
                <Link className="text-sm font-extrabold text-[#F25F3A]" to="/orders">
                  Back to orders
                </Link>
                <div className="mt-3 flex flex-wrap items-center gap-3">
                  <h1 className="font-mono text-3xl font-extrabold tracking-[-0.02em] text-[#071D34]">
                    {orderCode(order.id)}
                  </h1>
                  <StatusBadge status={order.current_status} />
                </div>
                <p className="mt-2 text-sm font-semibold text-[#667085]">
                  Created {formatDateTime(order.created_at)}
                </p>
              </div>
              <Link
                className="inline-flex min-h-11 items-center justify-center rounded-lg border border-[#DDE5E1] bg-white px-4 text-sm font-bold text-[#142033] hover:bg-[#F7F8F6]"
                to={trackingOnly ? `/orders/${order.id}` : `/orders/${order.id}/tracking`}
              >
                {trackingOnly ? 'View details' : 'Open tracking'}
              </Link>
            </div>

            {flash ? (
              <p className="mb-5 rounded-lg border border-[#BFE9DF] bg-[#DDF5EF] p-4 text-sm font-bold text-[#0F766E]">
                {flash}
              </p>
            ) : null}
            {error ? (
              <p className="mb-5 rounded-lg border border-[#F1B5B5] bg-[#FDE7E7] p-4 text-sm font-bold text-[#B42318]">
                {error}
              </p>
            ) : null}

            <div className="grid gap-6 xl:grid-cols-[1fr_380px]">
              <div className="grid gap-6">
                {!trackingOnly ? (
                  <section className="rounded-2xl border border-[#DDE5E1] bg-white p-5 sm:p-6">
                    <RouteRail
                      drop={order.drop_address}
                      dropZone={`${order.drop_zone_name} / ${order.drop_postal_code}`}
                      pickup={order.pickup_address}
                      pickupZone={`${order.pickup_zone_name} / ${order.pickup_postal_code}`}
                    />
                    <div className="mt-6 grid gap-4 md:grid-cols-4">
                      <DetailFact label="Status" value={statusLabel(order.current_status)} />
                      <DetailFact label="Payment" value={order.payment_type} />
                      <DetailFact label="Order type" value={order.order_type} />
                      <DetailFact
                        label="Agent"
                        value={
                          order.current_agent_id
                            ? `Agent #${order.current_agent_id}`
                            : 'Awaiting assignment'
                        }
                      />
                    </div>
                  </section>
                ) : null}

                {tracking ? (
                  <TrackingTimeline
                    currentStatus={tracking.current_status}
                    history={tracking.history}
                  />
                ) : null}
              </div>

              <aside className="grid content-start gap-5">
                <PriceBreakdown
                  actualWeight={order.actual_weight_kg}
                  billableWeight={order.billable_weight_kg}
                  codSurcharge={order.cod_surcharge}
                  deliveryCharge={order.delivery_charge}
                  destinationZone={order.drop_zone_name}
                  orderType={order.order_type}
                  originZone={order.pickup_zone_name}
                  ratePerKg={order.rate_per_kg}
                  totalCharge={order.total_charge}
                  volumetricWeight={order.volumetric_weight_kg}
                />

                <section className="rounded-xl border border-[#DDE5E1] bg-white p-5">
                  <p className="text-xs font-extrabold uppercase tracking-[0.1em] text-[#667085]">
                    Package
                  </p>
                  <div className="mt-4 grid gap-3 text-sm font-semibold text-[#667085]">
                    {order.package_description ? (
                      <FactLine label="Contents" value={order.package_description} />
                    ) : null}
                    <FactLine label="Dimensions" value={`${order.length_cm} x ${order.breadth_cm} x ${order.height_cm} cm`} />
                    <FactLine label="Actual weight" value={`${order.actual_weight_kg} kg`} />
                    <FactLine label="Total" value={formatCurrency(order.total_charge)} />
                  </div>
                </section>

                {order.is_fragile || order.delivery_instructions ? (
                  <section className="rounded-xl border border-[#DDE5E1] bg-white p-5">
                    <p className="text-xs font-extrabold uppercase tracking-[0.1em] text-[#667085]">
                      Handling
                    </p>
                    {order.is_fragile ? (
                      <div className="mt-4 rounded-lg border border-[#F8D79B] bg-[#FFF8EB] p-3 text-sm font-bold text-[#8A4B00]">
                        Fragile package - handle with care
                      </div>
                    ) : null}
                    {order.delivery_instructions ? (
                      <div className="mt-4">
                        <p className="text-xs font-extrabold uppercase tracking-[0.08em] text-[#667085]">
                          Delivery instructions
                        </p>
                        <p className="mt-2 text-sm font-semibold leading-6 text-[#142033]">
                          {order.delivery_instructions}
                        </p>
                      </div>
                    ) : null}
                  </section>
                ) : null}

                {order.current_status === 'FAILED' ? (
                  <section className="rounded-xl border border-[#F1B5B5] bg-white p-5">
                    <div className="flex items-center gap-3">
                      <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#FDE7E7] text-[#D64545]">
                        <Icon name="alert" className="h-5 w-5" />
                      </span>
                      <div>
                        <h2 className="font-extrabold text-[#142033]">Reschedule delivery</h2>
                        <p className="text-sm font-semibold text-[#667085]">
                          Choose a future date for the next attempt.
                        </p>
                      </div>
                    </div>
                    <form className="mt-5 grid gap-4" onSubmit={handleReschedule}>
                      <FormField label="New delivery date">
                        <TextInput
                          min={tomorrowDateValue()}
                          onChange={(event) => setScheduledDate(event.target.value)}
                          required
                          type="date"
                          value={scheduledDate}
                        />
                      </FormField>
                      <Button disabled={isRescheduling} type="submit">
                        <Icon name="calendar" className="h-4 w-4" />
                        {isRescheduling ? 'Rescheduling...' : 'Reschedule'}
                      </Button>
                    </form>
                  </section>
                ) : null}
              </aside>
            </div>
          </>
        ) : (
          <p className="rounded-lg border border-[#F1B5B5] bg-[#FDE7E7] p-4 text-sm font-bold text-[#B42318]">
            {error || 'Order not found'}
          </p>
        )}
      </div>
    </div>
  )
}

function DetailFact({ label, value }: { label: string; value: string }) {
  return (
    <div className="rounded-xl bg-[#F7F8F6] p-4">
      <p className="text-xs font-extrabold uppercase tracking-[0.08em] text-[#667085]">
        {label}
      </p>
      <p className="mt-2 font-extrabold text-[#142033]">{value}</p>
    </div>
  )
}

function FactLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span>{label}</span>
      <span className="text-right font-extrabold text-[#142033]">{value}</span>
    </div>
  )
}
