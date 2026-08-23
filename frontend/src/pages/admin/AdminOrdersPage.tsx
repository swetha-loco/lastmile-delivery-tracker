import { useEffect, useMemo, useState } from 'react'

import type {
  AgentPublic,
  OrderDetail,
  OrderPage,
  OrderStatus,
  TrackingResponse,
  Zone,
} from '../../api/client'
import {
  ApiError,
  assignOrder,
  autoAssignOrder,
  getOrder,
  getTracking,
  listAdminOrders,
  listAgents,
  listZones,
  overrideOrderStatus,
} from '../../api/client'
import { PriceBreakdown } from '../../components/orders/PriceBreakdown'
import { RouteRail } from '../../components/orders/RouteRail'
import { StatusBadge } from '../../components/orders/StatusBadge'
import { Button } from '../../components/ui/Button'
import { FormField, SelectInput, TextArea } from '../../components/ui/FormField'
import { Icon } from '../../components/ui/Icon'
import { useAuth } from '../../lib/auth'
import { formatCurrency, formatDateTime, orderCode, statusLabel } from '../../lib/format'

const orderStatuses: Array<OrderStatus | ''> = [
  '',
  'CREATED',
  'ASSIGNED',
  'PICKED_UP',
  'IN_TRANSIT',
  'OUT_FOR_DELIVERY',
  'DELIVERED',
  'FAILED',
  'RESCHEDULED',
]

export default function AdminOrdersPage() {
  const { token } = useAuth()
  const [orders, setOrders] = useState<OrderPage | null>(null)
  const [agents, setAgents] = useState<AgentPublic[]>([])
  const [zones, setZones] = useState<Zone[]>([])
  const [selectedId, setSelectedId] = useState<number | null>(null)
  const [selectedOrder, setSelectedOrder] = useState<OrderDetail | null>(null)
  const [tracking, setTracking] = useState<TrackingResponse | null>(null)
  const [filters, setFilters] = useState({ status: '', zoneId: '', agentId: '' })
  const [assignAgentId, setAssignAgentId] = useState('')
  const [overrideTarget, setOverrideTarget] = useState<OrderStatus>('CREATED')
  const [overrideReason, setOverrideReason] = useState('')
  const [notice, setNotice] = useState('')
  const [error, setError] = useState('')
  const [isBusy, setIsBusy] = useState(false)
  const [isLoading, setIsLoading] = useState(true)

  const availableAgents = useMemo(
    () => agents.filter((agent) => agent.availability === 'AVAILABLE'),
    [agents],
  )
  const selectedIsAssignable =
    selectedOrder?.current_status === 'CREATED' ||
    selectedOrder?.current_status === 'RESCHEDULED'

  async function loadLists() {
    if (!token) return
    setIsLoading(true)
    try {
      const [orderPage, agentPage, zoneRows] = await Promise.all([
        listAdminOrders(token, filters),
        listAgents(token),
        listZones(token),
      ])
      setOrders(orderPage)
      setAgents(agentPage.items)
      setZones(zoneRows)
      setSelectedId((current) => current ?? orderPage.items[0]?.id ?? null)
      setError('')
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to load operations')
    } finally {
      setIsLoading(false)
    }
  }

  async function loadSelected(orderId: number) {
    if (!token) return
    try {
      const [detail, timeline] = await Promise.all([
        getOrder(token, String(orderId)),
        getTracking(token, String(orderId)),
      ])
      setSelectedOrder(detail)
      setTracking(timeline)
      setAssignAgentId('')
      setOverrideTarget(detail.current_status)
      setOverrideReason('')
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to load order detail')
    }
  }

  useEffect(() => {
    void loadLists()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token, filters.status, filters.zoneId, filters.agentId])

  useEffect(() => {
    if (selectedId) void loadSelected(selectedId)
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [selectedId, token])

  async function runAction(action: () => Promise<OrderDetail>, success: string) {
    setIsBusy(true)
    setError('')
    setNotice('')
    try {
      const updated = await action()
      setSelectedOrder(updated)
      setSelectedId(updated.id)
      setNotice(success)
      await Promise.all([loadLists(), loadSelected(updated.id)])
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Action failed')
    } finally {
      setIsBusy(false)
    }
  }

  return (
    <div className="px-4 py-6 sm:px-8 lg:px-8">
      <div className="mx-auto max-w-[1500px]">
        <div className="mb-6 flex flex-wrap items-start justify-between gap-4">
          <div>
            <h1 className="text-3xl font-extrabold tracking-[-0.02em] text-[#071D34]">
              Operations
            </h1>
            <p className="mt-1 text-sm font-semibold text-[#667085]">
              Monitor and manage delivery orders in real time.
            </p>
          </div>
        </div>

        {error ? <Feedback tone="error" message={error} /> : null}
        {notice ? <Feedback tone="success" message={notice} /> : null}

        <section className="mb-6 rounded-xl border border-[#DDE5E1] bg-white p-4">
          <div className="grid gap-4 md:grid-cols-3">
            <FormField label="Status">
              <SelectInput
                value={filters.status}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, status: event.target.value }))
                }
              >
                {orderStatuses.map((status) => (
                  <option key={status || 'all'} value={status}>
                    {status ? statusLabel(status) : 'All statuses'}
                  </option>
                ))}
              </SelectInput>
            </FormField>
            <FormField label="Zone">
              <SelectInput
                value={filters.zoneId}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, zoneId: event.target.value }))
                }
              >
                <option value="">All zones</option>
                {zones.map((zone) => (
                  <option key={zone.id} value={zone.id}>
                    {zone.name}
                  </option>
                ))}
              </SelectInput>
            </FormField>
            <FormField label="Agent">
              <SelectInput
                value={filters.agentId}
                onChange={(event) =>
                  setFilters((current) => ({ ...current, agentId: event.target.value }))
                }
              >
                <option value="">All agents</option>
                {agents.map((agent) => (
                  <option key={agent.id} value={agent.id}>
                    {agent.name} ({agent.availability})
                  </option>
                ))}
              </SelectInput>
            </FormField>
          </div>
        </section>

        <div className="grid gap-5 xl:grid-cols-[minmax(0,1fr)_380px]">
          <section className="overflow-hidden rounded-xl border border-[#DDE5E1] bg-white">
            <div className="overflow-x-auto">
              <div className="min-w-[780px]">
                <div className="grid grid-cols-[120px_1fr_150px_145px_120px] gap-4 border-b border-[#DDE5E1] bg-[#F7F8F6] px-4 py-3 text-xs font-extrabold uppercase tracking-[0.08em] text-[#667085] max-lg:hidden">
                  <span>Order</span>
                  <span>Route</span>
                  <span>Agent</span>
                  <span>Status</span>
                  <span>Amount</span>
                </div>
            {isLoading ? (
              <div className="grid gap-2 p-4">
                {Array.from({ length: 8 }).map((_, index) => (
                  <div key={index} className="h-16 animate-pulse rounded-lg bg-[#F1F5F2]" />
                ))}
              </div>
            ) : orders?.items.length ? (
              orders.items.map((order) => (
                <button
                  key={order.id}
                  className={`grid w-full gap-4 border-b border-[#DDE5E1] px-4 py-4 text-left transition hover:bg-[#F7F8F6] lg:grid-cols-[120px_1fr_150px_145px_120px] lg:items-center ${
                    selectedId === order.id ? 'bg-[#EFF6FF]' : ''
                  }`}
                  type="button"
                  onClick={() => setSelectedId(order.id)}
                >
                  <div>
                    <p className="font-mono text-sm font-extrabold">{orderCode(order.id)}</p>
                    <p className="mt-1 text-xs font-semibold text-[#667085]">
                      {formatDateTime(order.created_at)}
                    </p>
                  </div>
                  <div className="flex items-center gap-3">
                    <Icon name="route" className="h-5 w-5 text-[#128C7E]" />
                    <div className="min-w-0">
                      <p className="truncate text-sm font-extrabold">
                        {order.pickup_zone_name} {'->'} {order.drop_zone_name}
                      </p>
                      <p className="truncate text-sm font-medium text-[#667085]">
                        {order.pickup_address} {'->'} {order.drop_address}
                      </p>
                    </div>
                  </div>
                  <p className="text-sm font-semibold text-[#667085]">
                    {order.current_agent_id ? `Agent #${order.current_agent_id}` : 'Unassigned'}
                  </p>
                  <StatusBadge status={order.current_status} />
                  <p className="font-extrabold">{formatCurrency(order.total_charge)}</p>
                </button>
              ))
            ) : (
              <p className="p-8 text-center text-sm font-semibold text-[#667085]">
                No orders match these filters.
              </p>
            )}
              </div>
            </div>
          </section>

          <aside className="rounded-xl border border-[#DDE5E1] bg-white p-5 xl:sticky xl:top-6 xl:max-h-[calc(100vh-3rem)] xl:overflow-y-auto">
            {selectedOrder ? (
              <div className="grid gap-5">
                <div className="flex items-start justify-between gap-3">
                  <div>
                    <p className="text-xs font-extrabold uppercase tracking-[0.1em] text-[#667085]">
                      Order
                    </p>
                    <h2 className="font-mono text-2xl font-extrabold text-[#071D34]">
                      {orderCode(selectedOrder.id)}
                    </h2>
                  </div>
                  <StatusBadge status={selectedOrder.current_status} />
                </div>

                {selectedIsAssignable ? (
                  <>
                    <div className="flex gap-2">
                      <Button
                        disabled={isBusy || !assignAgentId}
                        type="button"
                        onClick={() =>
                          runAction(
                            () => assignOrder(token!, selectedOrder.id, Number(assignAgentId)),
                            'Order assigned.',
                          )
                        }
                      >
                        Manual assign
                      </Button>
                      <Button
                        disabled={isBusy}
                        type="button"
                        variant="secondary"
                        onClick={() =>
                          runAction(
                            () => autoAssignOrder(token!, selectedOrder.id),
                            'Auto-assignment complete.',
                          )
                        }
                      >
                        Auto assign
                      </Button>
                    </div>

                    <FormField label="Available agent">
                      <SelectInput
                        value={assignAgentId}
                        onChange={(event) => setAssignAgentId(event.target.value)}
                      >
                        <option value="">Choose an available agent</option>
                        {availableAgents.map((agent) => (
                          <option key={agent.id} value={agent.id}>
                            {agent.name} · {agent.current_zone_id ? `Zone ${agent.current_zone_id}` : 'No zone'}
                          </option>
                        ))}
                      </SelectInput>
                    </FormField>
                  </>
                ) : (
                  <p className="rounded-lg bg-[#F7F8F6] p-3 text-sm font-bold text-[#667085]">
                    Assignment actions are available only for Created or Rescheduled orders.
                  </p>
                )}

                <RouteRail
                  drop={selectedOrder.drop_address}
                  dropZone={selectedOrder.drop_zone_name}
                  pickup={selectedOrder.pickup_address}
                  pickupZone={selectedOrder.pickup_zone_name}
                />

                <div className="grid gap-2 text-sm font-semibold text-[#667085]">
                  <Fact label="Customer" value={`Customer #${selectedOrder.customer_id}`} />
                  <Fact
                    label="Assigned agent"
                    value={
                      selectedOrder.current_agent_id
                        ? `Agent #${selectedOrder.current_agent_id}`
                        : 'Unassigned'
                    }
                  />
                  <Fact label="Order type" value={selectedOrder.order_type} />
                  <Fact label="Payment" value={selectedOrder.payment_type} />
                </div>

                <PriceBreakdown
                  actualWeight={selectedOrder.actual_weight_kg}
                  billableWeight={selectedOrder.billable_weight_kg}
                  codSurcharge={selectedOrder.cod_surcharge}
                  deliveryCharge={selectedOrder.delivery_charge}
                  ratePerKg={selectedOrder.rate_per_kg}
                  totalCharge={selectedOrder.total_charge}
                  volumetricWeight={selectedOrder.volumetric_weight_kg}
                />

                <section className="rounded-xl border border-[#F8D79B] bg-[#FFF8EB] p-4">
                  <h3 className="font-extrabold text-[#8A4B00]">Override status</h3>
                  <div className="mt-3 grid gap-3">
                    <FormField label="Target status">
                      <SelectInput
                        value={overrideTarget}
                        onChange={(event) => setOverrideTarget(event.target.value as OrderStatus)}
                      >
                        {orderStatuses.filter(Boolean).map((status) => (
                          <option key={status} value={status}>
                            {statusLabel(status as OrderStatus)}
                          </option>
                        ))}
                      </SelectInput>
                    </FormField>
                    <FormField label="Reason">
                      <TextArea
                        value={overrideReason}
                        onChange={(event) => setOverrideReason(event.target.value)}
                        placeholder="Required for audit history"
                      />
                    </FormField>
                    <Button
                      disabled={isBusy || !overrideReason.trim()}
                      type="button"
                      variant="secondary"
                      onClick={() =>
                        runAction(
                          () =>
                            overrideOrderStatus(
                              token!,
                              selectedOrder.id,
                              overrideTarget,
                              overrideReason,
                            ),
                          'Status overridden.',
                        )
                      }
                    >
                      Override status
                    </Button>
                  </div>
                </section>

                <section>
                  <div className="mb-3 flex items-center justify-between">
                    <h3 className="font-extrabold">Status history</h3>
                  </div>
                  <div className="grid gap-3">
                    {tracking?.history.slice(-4).reverse().map((entry) => (
                      <div key={entry.id} className="flex gap-3 text-sm">
                        <span className="mt-1.5 h-2.5 w-2.5 rounded-full bg-[#128C7E]" />
                        <div>
                          <p className="font-extrabold">{statusLabel(entry.to_status)}</p>
                          <p className="font-semibold text-[#667085]">
                            {formatDateTime(entry.created_at)}
                          </p>
                          {entry.reason ? (
                            <p className="mt-1 font-medium text-[#667085]">{entry.reason}</p>
                          ) : null}
                        </div>
                      </div>
                    ))}
                  </div>
                </section>
              </div>
            ) : (
              <p className="text-sm font-semibold text-[#667085]">
                Select an order to manage assignment and status.
              </p>
            )}
          </aside>
        </div>
      </div>
    </div>
  )
}

function Fact({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex justify-between gap-4 border-b border-[#DDE5E1] py-2">
      <span>{label}</span>
      <span className="text-right font-extrabold text-[#142033]">{value}</span>
    </div>
  )
}

function Feedback({ tone, message }: { tone: 'error' | 'success'; message: string }) {
  return (
    <p
      className={`mb-4 rounded-lg border p-3 text-sm font-bold ${
        tone === 'success'
          ? 'border-[#BFE9DF] bg-[#DDF5EF] text-[#0F766E]'
          : 'border-[#F1B5B5] bg-[#FDE7E7] text-[#B42318]'
      }`}
    >
      {message}
    </p>
  )
}
