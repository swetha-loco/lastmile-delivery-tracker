import type { OrderStatus } from '../../api/client'
import { statusLabel } from '../../lib/format'

const statusStyles: Record<OrderStatus, string> = {
  CREATED: 'bg-[#FFF2D8] text-[#A15C00] border-[#F8D79B]',
  ASSIGNED: 'bg-[#E8F1FF] text-[#175CD3] border-[#C7D7FE]',
  PICKED_UP: 'bg-[#DDF5EF] text-[#0F766E] border-[#BFE9DF]',
  IN_TRANSIT: 'bg-[#DDF5EF] text-[#0F766E] border-[#BFE9DF]',
  OUT_FOR_DELIVERY: 'bg-[#DDF5EF] text-[#0F766E] border-[#BFE9DF]',
  DELIVERED: 'bg-[#E7F7E8] text-[#267A35] border-[#C8EACB]',
  FAILED: 'bg-[#FDE7E7] text-[#B42318] border-[#F4B8B8]',
  RESCHEDULED: 'bg-[#FFF2D8] text-[#A15C00] border-[#F8D79B]',
}

export function StatusBadge({ status }: { status: OrderStatus }) {
  return (
    <span
      className={`inline-flex w-fit items-center whitespace-nowrap rounded-md border px-2.5 py-1 text-xs font-extrabold uppercase tracking-[0.04em] ${statusStyles[status]}`}
    >
      {statusLabel(status)}
    </span>
  )
}
