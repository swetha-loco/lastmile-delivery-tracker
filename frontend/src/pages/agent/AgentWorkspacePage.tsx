import { useEffect, useMemo, useState } from 'react'
import { Link } from 'react-router'

import type {
  AgentAvailability,
  AgentProfile,
  OrderDetail,
  OrderStatus,
  OrderSummary,
  TrackingResponse,
} from '../../api/client'
import {
  ApiError,
  getAgentProfile,
  getOrder,
  getTracking,
  listAgentOrders,
  updateAgentAvailability,
  updateAgentLocation,
  updateAgentOrderStatus,
} from '../../api/client'
import { RouteRail } from '../../components/orders/RouteRail'
import { StatusBadge } from '../../components/orders/StatusBadge'
import { TrackingTimeline } from '../../components/orders/TrackingTimeline'
import { Button } from '../../components/ui/Button'
import { TextArea } from '../../components/ui/FormField'
import { Icon } from '../../components/ui/Icon'
import { useAuth } from '../../lib/auth'
import { formatCurrency, formatDateTime, orderCode, statusLabel } from '../../lib/format'

const activeStatuses: OrderStatus[] = [
  'ASSIGNED',
  'PICKED_UP',
  'IN_TRANSIT',
  'OUT_FOR_DELIVERY',
]

const nextActions: Partial<Record<OrderStatus, { label: string; target: OrderStatus }>> = {
  ASSIGNED: { label: 'Mark Picked Up', target: 'PICKED_UP' },
  PICKED_UP: { label: 'Mark In Transit', target: 'IN_TRANSIT' },
  IN_TRANSIT: { label: 'Out for Delivery', target: 'OUT_FOR_DELIVERY' },
  OUT_FOR_DELIVERY: { label: 'Delivered', target: 'DELIVERED' },
}

export default function AgentWorkspacePage() {
  const { token } = useAuth()
  const [orders, setOrders] = useState<OrderSummary[]>([])
  const [currentOrder, setCurrentOrder] = useState<OrderDetail | null>(null)
  const [tracking, setTracking] = useState<TrackingResponse | null>(null)
  const [profile, setProfile] = useState<AgentProfile | null>(null)
  const [failureReason, setFailureReason] = useState('')
  const [showFailure, setShowFailure] = useState(false)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [isLoading, setIsLoading] = useState(true)
  const [isBusy, setIsBusy] = useState(false)

  const activeSummary = useMemo(
    () =>
      orders.find((order) => activeStatuses.includes(order.current_status)) ??
      orders.find((order) => order.current_status === 'FAILED' || order.current_status === 'RESCHEDULED') ??
      null,
    [orders],
  )
  const action = currentOrder ? nextActions[currentOrder.current_status] : undefined
  const shownAvailability: AgentAvailability =
    currentOrder && activeStatuses.includes(currentOrder.current_status)
      ? 'BUSY'
      : (profile?.availability ?? 'OFFLINE')

  async function loadWorkspace() {
    if (!token) return
    setIsLoading(true)
    try {
      const [nextProfile, page] = await Promise.all([
        getAgentProfile(token),
        listAgentOrders(token, 1, 20),
      ])
      setProfile(nextProfile)
      setOrders(page.items)
      const active = page.items.find((order) => activeStatuses.includes(order.current_status))
      const focus = active ?? page.items[0]
      if (focus) {
        const [detail, timeline] = await Promise.all([
          getOrder(token, String(focus.id)),
          getTracking(token, String(focus.id)),
        ])
        setCurrentOrder(detail)
        setTracking(timeline)
      } else {
        setCurrentOrder(null)
        setTracking(null)
      }
      setError('')
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to load agent workspace')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void loadWorkspace()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  async function setAvailability(availability: Exclude<AgentAvailability, 'BUSY'>) {
    if (!token) return
    setIsBusy(true)
    setError('')
    setNotice('')
    try {
      const nextProfile = await updateAgentAvailability(token, availability)
      setProfile(nextProfile)
      setNotice(`Availability set to ${availability.toLowerCase().replace('_', ' ')}.`)
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to update availability')
    } finally {
      setIsBusy(false)
    }
  }

  async function updateLocation() {
    if (!token) return
    if (!navigator.geolocation) {
      setError('This browser does not support location capture.')
      return
    }
    setIsBusy(true)
    setError('')
    setNotice('')
    navigator.geolocation.getCurrentPosition(
      (position) => {
        void updateAgentLocation(token, position.coords.latitude, position.coords.longitude)
          .then((nextProfile) => {
            setProfile(nextProfile)
            setNotice('Current location updated.')
          })
          .catch((exc: unknown) => {
            setError(exc instanceof ApiError ? exc.message : 'Unable to update location')
          })
          .finally(() => setIsBusy(false))
      },
      () => {
        setError('Location permission was denied or unavailable.')
        setIsBusy(false)
      },
      { enableHighAccuracy: true, timeout: 8000 },
    )
  }

  async function progress(targetStatus: OrderStatus, reason?: string) {
    if (!token || !currentOrder) return
    setIsBusy(true)
    setError('')
    setNotice('')
    try {
      const updated = await updateAgentOrderStatus(token, currentOrder.id, targetStatus, reason)
      setCurrentOrder(updated)
      setNotice(`Order moved to ${statusLabel(targetStatus)}.`)
      setFailureReason('')
      setShowFailure(false)
      await loadWorkspace()
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to update delivery status')
    } finally {
      setIsBusy(false)
    }
  }

  return (
    <div className="px-4 py-5 sm:px-6 lg:px-8 lg:py-8">
      <div className="mx-auto max-w-6xl">
        <div className="grid gap-5 lg:grid-cols-[320px_1fr]">
          <aside className="grid content-start gap-4">
            <section className="rounded-2xl border border-[#DDE5E1] bg-white p-5">
              <p className="text-xs font-extrabold uppercase tracking-[0.1em] text-[#667085]">
                Agent state
              </p>
              <div className="mt-3 flex items-center justify-between gap-4">
                <div>
                  <p className="text-2xl font-extrabold text-[#071D34]">
                    {shownAvailability}
                  </p>
                  <p className="mt-1 text-sm font-semibold text-[#667085]">
                    BUSY is controlled by assignment.
                  </p>
                </div>
                <AvailabilityDot availability={shownAvailability} />
              </div>
              <div className="mt-5 grid grid-cols-2 gap-2">
                <Button
                  disabled={isBusy || shownAvailability === 'BUSY'}
                  type="button"
                  variant={profile?.availability === 'AVAILABLE' ? 'primary' : 'secondary'}
                  onClick={() => void setAvailability('AVAILABLE')}
                >
                  Available
                </Button>
                <Button
                  disabled={isBusy || shownAvailability === 'BUSY'}
                  type="button"
                  variant="secondary"
                  onClick={() => void setAvailability('OFFLINE')}
                >
                  Offline
                </Button>
              </div>
              <Button
                className="mt-3 w-full"
                disabled={isBusy}
                type="button"
                variant="ghost"
                onClick={() => void updateLocation()}
              >
                <Icon name="pin" className="h-4 w-4" />
                Update Current Location
              </Button>
            </section>

            <section className="rounded-2xl border border-[#DDE5E1] bg-white p-5">
              <div className="flex items-center justify-between gap-3">
                <div>
                  <p className="text-xs font-extrabold uppercase tracking-[0.1em] text-[#667085]">
                    Queue
                  </p>
                  <h2 className="mt-1 text-xl font-extrabold text-[#071D34]">
                    Assigned deliveries
                  </h2>
                </div>
                <Link className="text-sm font-extrabold text-[#F25F3A]" to="/agent/orders">
                  View all
                </Link>
              </div>
              <div className="mt-4 grid gap-2">
                {orders.slice(0, 4).map((order) => (
                  <button
                    key={order.id}
                    className={`rounded-lg border p-3 text-left transition hover:border-[#BFE9DF] ${
                      activeSummary?.id === order.id
                        ? 'border-[#BFE9DF] bg-[#DDF5EF]'
                        : 'border-[#DDE5E1] bg-[#F7F8F6]'
                    }`}
                    type="button"
                    onClick={() => {
                      setCurrentOrder(null)
                      void Promise.all([
                        getOrder(token ?? '', String(order.id)),
                        getTracking(token ?? '', String(order.id)),
                      ]).then(([detail, timeline]) => {
                        setCurrentOrder(detail)
                        setTracking(timeline)
                      })
                    }}
                  >
                    <p className="font-mono text-sm font-extrabold text-[#071D34]">
                      {orderCode(order.id)}
                    </p>
                    <p className="mt-1 line-clamp-1 text-sm font-semibold text-[#667085]">
                      {order.pickup_zone_name} to {order.drop_zone_name}
                    </p>
                  </button>
                ))}
                {orders.length === 0 ? (
                  <p className="rounded-lg bg-[#F7F8F6] p-4 text-sm font-semibold text-[#667085]">
                    You're available. No delivery is assigned right now.
                  </p>
                ) : null}
              </div>
            </section>
          </aside>

          <main className="grid gap-5">
            {notice ? <Feedback tone="success" message={notice} /> : null}
            {error ? <Feedback tone="error" message={error} /> : null}
            {isLoading ? (
              <div className="h-[620px] animate-pulse rounded-2xl bg-white" />
            ) : currentOrder ? (
              <>
                <section className="rounded-2xl border border-[#DDE5E1] bg-white p-5 sm:p-6">
                  <div className="flex flex-wrap items-start justify-between gap-4">
                    <div>
                      <p className="text-xs font-extrabold uppercase tracking-[0.1em] text-[#667085]">
                        Current delivery
                      </p>
                      <div className="mt-2 flex flex-wrap items-center gap-3">
                        <h1 className="font-mono text-3xl font-extrabold text-[#071D34]">
                          {orderCode(currentOrder.id)}
                        </h1>
                        <StatusBadge status={currentOrder.current_status} />
                      </div>
                      <p className="mt-2 text-sm font-semibold text-[#667085]">
                        Created {formatDateTime(currentOrder.created_at)}
                      </p>
                    </div>
                    <div className="min-w-40 rounded-xl bg-[#071D34] p-4 text-white">
                      <p className="text-xs font-extrabold uppercase tracking-[0.1em] text-white/60">
                        Collect
                      </p>
                      <p className="mt-1 text-xl font-extrabold">
                        {formatCurrency(currentOrder.total_charge)}
                      </p>
                    </div>
                  </div>
                  <div className="mt-6">
                    <RouteRail
                      drop={currentOrder.drop_address}
                      dropZone={`${currentOrder.drop_zone_name} / ${currentOrder.drop_postal_code}`}
                      pickup={currentOrder.pickup_address}
                      pickupZone={`${currentOrder.pickup_zone_name} / ${currentOrder.pickup_postal_code}`}
                      spacious
                    />
                  </div>
                  {currentOrder.package_description ||
                  currentOrder.is_fragile ||
                  currentOrder.delivery_instructions ? (
                    <section className="mt-5 rounded-xl border border-[#DDE5E1] bg-[#F7F8F6] p-4">
                      <p className="text-xs font-extrabold uppercase tracking-[0.1em] text-[#667085]">
                        Package & handling
                      </p>
                      <div className="mt-3 grid gap-3 text-sm font-semibold text-[#667085]">
                        {currentOrder.package_description ? (
                          <div>
                            <span className="font-extrabold text-[#142033]">Package: </span>
                            {currentOrder.package_description}
                          </div>
                        ) : null}
                        {currentOrder.is_fragile ? (
                          <div className="rounded-lg border border-[#F8D79B] bg-[#FFF8EB] p-3 font-bold text-[#8A4B00]">
                            Fragile package - handle with care
                          </div>
                        ) : null}
                        {currentOrder.delivery_instructions ? (
                          <div>
                            <p className="text-xs font-extrabold uppercase tracking-[0.08em]">
                              Delivery instructions
                            </p>
                            <p className="mt-1 leading-6 text-[#142033]">
                              {currentOrder.delivery_instructions}
                            </p>
                          </div>
                        ) : null}
                      </div>
                    </section>
                  ) : null}
                  <AgentProgress status={currentOrder.current_status} />
                  {action ? (
                    <div className="mt-6 flex flex-wrap gap-3">
                      <Button
                        className="min-w-48"
                        disabled={isBusy}
                        type="button"
                        onClick={() => void progress(action.target)}
                      >
                        {action.label}
                      </Button>
                      {currentOrder.current_status === 'OUT_FOR_DELIVERY' ? (
                        <Button
                          disabled={isBusy}
                          type="button"
                          variant="danger"
                          onClick={() => setShowFailure(true)}
                        >
                          Mark Failed
                        </Button>
                      ) : null}
                    </div>
                  ) : (
                    <p className="mt-6 rounded-lg bg-[#F7F8F6] p-4 text-sm font-semibold text-[#667085]">
                      No next delivery action is available for this status.
                    </p>
                  )}
                </section>

                {showFailure ? (
                  <section className="rounded-2xl border border-[#F1B5B5] bg-white p-5">
                    <div className="flex items-center gap-3">
                      <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#FDE7E7] text-[#D64545]">
                        <Icon name="alert" />
                      </span>
                      <div>
                        <h2 className="font-extrabold text-[#142033]">Mark delivery failed</h2>
                        <p className="text-sm font-semibold text-[#667085]">
                          A reason is required and becomes part of the tracking history.
                        </p>
                      </div>
                    </div>
                    <TextArea
                      className="mt-4"
                      placeholder="Customer unavailable, address inaccessible, or another clear reason"
                      rows={4}
                      value={failureReason}
                      onChange={(event) => setFailureReason(event.target.value)}
                    />
                    <div className="mt-4 flex flex-wrap gap-3">
                      <Button
                        disabled={isBusy || failureReason.trim().length === 0}
                        type="button"
                        variant="danger"
                        onClick={() => void progress('FAILED', failureReason.trim())}
                      >
                        Confirm Failed
                      </Button>
                      <Button type="button" variant="secondary" onClick={() => setShowFailure(false)}>
                        Cancel
                      </Button>
                    </div>
                  </section>
                ) : null}

                {tracking ? (
                  <TrackingTimeline
                    currentStatus={tracking.current_status}
                    history={tracking.history}
                  />
                ) : null}
              </>
            ) : (
              <section className="rounded-2xl border border-[#DDE5E1] bg-white p-8 text-center">
                <span className="mx-auto flex h-14 w-14 items-center justify-center rounded-2xl bg-[#DDF5EF] text-[#128C7E]">
                  <Icon name="route" />
                </span>
                <h1 className="mt-4 text-2xl font-extrabold text-[#071D34]">
                  No active delivery
                </h1>
                <p className="mx-auto mt-2 max-w-md text-sm font-semibold leading-6 text-[#667085]">
                  Set yourself available, update your current location, and new assignments will
                  appear here when an admin assigns a delivery.
                </p>
              </section>
            )}
          </main>
        </div>
      </div>
    </div>
  )
}

function AgentProgress({ status }: { status: OrderStatus }) {
  const steps: OrderStatus[] = [
    'ASSIGNED',
    'PICKED_UP',
    'IN_TRANSIT',
    'OUT_FOR_DELIVERY',
    'DELIVERED',
  ]
  const index = steps.indexOf(status)
  return (
    <div className="mt-7 grid grid-cols-5 gap-1">
      {steps.map((step, stepIndex) => {
        const reached = index >= stepIndex
        const active = status === step
        return (
          <div key={step} className="relative grid justify-items-center gap-2">
            {stepIndex > 0 ? (
              <span
                className={`absolute right-1/2 top-4 h-0.5 w-full ${
                  reached ? 'bg-[#128C7E]' : 'bg-[#DDE5E1]'
                }`}
              />
            ) : null}
            <span
              className={`relative z-10 flex h-8 w-8 items-center justify-center rounded-full border ${
                active
                  ? 'border-[#F25F3A] bg-[#F25F3A] text-white'
                  : reached
                    ? 'border-[#128C7E] bg-[#DDF5EF] text-[#128C7E]'
                    : 'border-[#DDE5E1] bg-white text-[#98A2B3]'
              }`}
            >
              <Icon name={reached ? 'check' : 'box'} className="h-4 w-4" />
            </span>
            <span className="hidden max-w-24 text-center text-[10px] font-extrabold uppercase tracking-[0.04em] text-[#667085] sm:block">
              {statusLabel(step)}
            </span>
          </div>
        )
      })}
      {status === 'FAILED' ? (
        <p className="col-span-5 mt-3 rounded-lg border border-[#F1B5B5] bg-[#FDE7E7] p-3 text-sm font-bold text-[#B42318]">
          Delivery failed. The customer can reschedule a new attempt.
        </p>
      ) : null}
    </div>
  )
}

function AvailabilityDot({ availability }: { availability: AgentAvailability }) {
  const tone =
    availability === 'AVAILABLE'
      ? 'bg-[#128C7E]'
      : availability === 'BUSY'
        ? 'bg-[#D98613]'
        : 'bg-[#667085]'
  return <span className={`h-4 w-4 rounded-full ${tone}`} />
}

function Feedback({ tone, message }: { tone: 'error' | 'success'; message: string }) {
  return (
    <p
      className={`rounded-lg border p-3 text-sm font-bold ${
        tone === 'success'
          ? 'border-[#BFE9DF] bg-[#DDF5EF] text-[#0F766E]'
          : 'border-[#F1B5B5] bg-[#FDE7E7] text-[#B42318]'
      }`}
    >
      {message}
    </p>
  )
}
