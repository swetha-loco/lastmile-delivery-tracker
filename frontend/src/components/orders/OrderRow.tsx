import { Link } from 'react-router'

import type { OrderSummary } from '../../api/client'
import { formatCurrency, formatDateTime, orderCode } from '../../lib/format'
import { Icon } from '../ui/Icon'
import { StatusBadge } from './StatusBadge'

export function OrderRow({ order }: { order: OrderSummary }) {
  return (
    <Link
      className="grid gap-4 border-b border-[#DDE5E1] px-4 py-4 transition hover:bg-[#F7F8F6] md:grid-cols-[120px_1fr_150px_120px_120px] md:items-center"
      to={`/orders/${order.id}`}
    >
      <div>
        <p className="font-mono text-sm font-extrabold text-[#142033]">{orderCode(order.id)}</p>
        <p className="mt-1 text-xs font-semibold text-[#667085]">
          {formatDateTime(order.created_at)}
        </p>
      </div>

      <div className="flex items-center gap-3">
        <Icon name="route" className="h-5 w-5 shrink-0 text-[#128C7E]" />
        <div className="min-w-0">
          <p className="truncate text-sm font-extrabold text-[#142033]">
            {order.pickup_zone_name} {'->'} {order.drop_zone_name}
          </p>
          <p className="truncate text-sm font-medium text-[#667085]">
            {order.pickup_address} {'->'} {order.drop_address}
          </p>
        </div>
      </div>

      <StatusBadge status={order.current_status} />

      <p className="text-sm font-semibold text-[#667085]">
        {order.current_agent_id ? `Agent #${order.current_agent_id}` : 'Unassigned'}
      </p>

      <p className="text-right text-base font-extrabold text-[#142033] md:text-left">
        {formatCurrency(order.total_charge)}
      </p>
    </Link>
  )
}
