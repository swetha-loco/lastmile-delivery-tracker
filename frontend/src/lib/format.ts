import type { OrderStatus } from '../api/client'

export function formatCurrency(value: string | number): string {
  const amount = typeof value === 'number' ? value : Number(value)
  if (!Number.isFinite(amount)) return '₹0.00'
  return new Intl.NumberFormat('en-IN', {
    style: 'currency',
    currency: 'INR',
    minimumFractionDigits: 2,
  }).format(amount)
}

export function formatDateTime(value: string): string {
  return new Intl.DateTimeFormat('en-IN', {
    dateStyle: 'medium',
    timeStyle: 'short',
  }).format(new Date(value))
}

export function formatDate(value: string): string {
  return new Intl.DateTimeFormat('en-IN', { dateStyle: 'medium' }).format(
    new Date(value),
  )
}

export function statusLabel(status: OrderStatus): string {
  const labels: Record<OrderStatus, string> = {
    CREATED: 'Created',
    ASSIGNED: 'Assigned',
    PICKED_UP: 'Picked Up',
    IN_TRANSIT: 'In Transit',
    OUT_FOR_DELIVERY: 'Out for Delivery',
    DELIVERED: 'Delivered',
    FAILED: 'Failed',
    RESCHEDULED: 'Rescheduled',
  }
  return labels[status]
}

export function orderCode(id: number): string {
  return `LM-${String(id).padStart(5, '0')}`
}

export function tomorrowDateValue(): string {
  const date = new Date()
  date.setDate(date.getDate() + 1)
  return date.toISOString().slice(0, 10)
}
