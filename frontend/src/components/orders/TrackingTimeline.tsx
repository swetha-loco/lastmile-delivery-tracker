import type { OrderStatus, TrackingHistoryEntry } from '../../api/client'
import { formatDateTime, statusLabel } from '../../lib/format'
import { Icon } from '../ui/Icon'
import { StatusBadge } from './StatusBadge'

const milestoneOrder: OrderStatus[] = [
  'CREATED',
  'ASSIGNED',
  'PICKED_UP',
  'IN_TRANSIT',
  'OUT_FOR_DELIVERY',
  'DELIVERED',
]

export function TrackingTimeline({
  currentStatus,
  history,
}: {
  currentStatus: OrderStatus
  history: TrackingHistoryEntry[]
}) {
  const reached = new Set(history.map((item) => item.to_status))
  const currentIndex = milestoneOrder.indexOf(currentStatus)
  const isException = currentStatus === 'FAILED' || currentStatus === 'RESCHEDULED'

  return (
    <div className="grid gap-6">
      <div className="rounded-xl border border-[#DDE5E1] bg-white p-5">
        <div className="flex flex-wrap items-center justify-between gap-3">
          <div>
            <p className="text-xs font-extrabold uppercase tracking-[0.1em] text-[#667085]">
              Delivery Progress
            </p>
            <h2 className="mt-1 text-xl font-extrabold text-[#142033]">
              {statusLabel(currentStatus)}
            </h2>
          </div>
          <StatusBadge status={currentStatus} />
        </div>

        <div className="mt-7 grid grid-cols-6 gap-1">
          {milestoneOrder.map((status, index) => {
            const complete =
              reached.has(status) || (!isException && currentIndex >= index && currentIndex >= 0)
            const active = currentStatus === status
            return (
              <div key={status} className="relative grid justify-items-center gap-2">
                {index > 0 ? (
                  <span
                    className={`absolute right-1/2 top-4 h-0.5 w-full ${
                      complete ? 'bg-[#128C7E]' : 'bg-[#DDE5E1]'
                    }`}
                  />
                ) : null}
                <span
                  className={`relative z-10 flex h-8 w-8 items-center justify-center rounded-full border ${
                    active
                      ? 'border-[#F25F3A] bg-[#F25F3A] text-white'
                      : complete
                        ? 'border-[#128C7E] bg-[#DDF5EF] text-[#128C7E]'
                        : 'border-[#DDE5E1] bg-white text-[#98A2B3]'
                  }`}
                >
                  <Icon name={complete ? 'check' : 'box'} className="h-4 w-4" />
                </span>
                <span className="hidden max-w-24 text-center text-[11px] font-extrabold uppercase tracking-[0.04em] text-[#667085] sm:block">
                  {statusLabel(status)}
                </span>
              </div>
            )
          })}
        </div>

        {isException ? (
          <div className="mt-6 rounded-lg border border-[#F8D79B] bg-[#FFF8EB] p-4 text-sm font-semibold text-[#8A4B00]">
            {currentStatus === 'FAILED'
              ? 'This delivery needs attention. Choose a new date to schedule another attempt.'
              : 'A new delivery attempt is planned and awaiting assignment.'}
          </div>
        ) : null}
      </div>

      <div className="rounded-xl border border-[#DDE5E1] bg-white p-5">
        <h3 className="text-base font-extrabold text-[#142033]">Complete timeline</h3>
        <div className="mt-5 grid gap-0">
          {history.map((entry, index) => (
            <div key={entry.id} className="grid grid-cols-[28px_1fr] gap-4">
              <div className="relative grid justify-items-center">
                <span
                  className={`mt-1 h-3 w-3 rounded-full ${
                    entry.to_status === 'FAILED'
                      ? 'bg-[#D64545]'
                      : entry.to_status === 'RESCHEDULED'
                        ? 'bg-[#D98613]'
                        : 'bg-[#128C7E]'
                  }`}
                />
                {index < history.length - 1 ? (
                  <span className="min-h-12 w-px bg-[#DDE5E1]" />
                ) : null}
              </div>
              <div className="pb-5">
                <div className="flex flex-wrap items-start justify-between gap-3">
                  <div>
                    <p className="font-extrabold text-[#142033]">
                      {statusLabel(entry.to_status)}
                    </p>
                    <p className="mt-1 text-sm font-medium text-[#667085]">
                      {formatDateTime(entry.created_at)} by {entry.actor_role.toLowerCase()}
                    </p>
                  </div>
                  <StatusBadge status={entry.to_status} />
                </div>
                {entry.reason ? (
                  <p className="mt-3 rounded-lg bg-[#F7F8F6] px-3 py-2 text-sm font-medium text-[#667085]">
                    {entry.reason}
                  </p>
                ) : null}
              </div>
            </div>
          ))}
          {history.length === 0 ? (
            <p className="rounded-lg bg-[#F7F8F6] p-4 text-sm font-semibold text-[#667085]">
              No tracking events yet.
            </p>
          ) : null}
        </div>
      </div>
    </div>
  )
}
