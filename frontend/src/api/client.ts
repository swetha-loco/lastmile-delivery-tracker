const apiBaseUrl = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')

export type UserRole = 'CUSTOMER' | 'DELIVERY_AGENT' | 'ADMIN'
export type OrderType = 'B2B' | 'B2C'
export type PaymentType = 'PREPAID' | 'COD'
export type OrderStatus =
  | 'CREATED'
  | 'ASSIGNED'
  | 'PICKED_UP'
  | 'IN_TRANSIT'
  | 'OUT_FOR_DELIVERY'
  | 'DELIVERED'
  | 'FAILED'
  | 'RESCHEDULED'

export type HealthResponse = {
  status: string
  database: string
}

export type User = {
  id: number
  name: string
  email: string
  phone: string | null
  role: UserRole
}

export type TokenResponse = {
  access_token: string
  token_type: 'bearer'
}

export type OrderInput = {
  pickup_address: string
  drop_address: string
  length_cm: string
  breadth_cm: string
  height_cm: string
  actual_weight_kg: string
  order_type: OrderType
  payment_type: PaymentType
}

export type ResolvedAddress = {
  formatted_address: string
  postal_code: string
  latitude: string
  longitude: string
  zone_id: number
  zone_name: string
}

export type QuoteResponse = {
  pickup: ResolvedAddress
  drop: ResolvedAddress
  actual_weight_kg: string
  volumetric_weight_kg: string
  billable_weight_kg: string
  order_type: OrderType
  payment_type: PaymentType
  rate_per_kg: string
  delivery_charge: string
  cod_surcharge: string
  total_charge: string
}

export type OrderSummary = {
  id: number
  pickup_address: string
  pickup_zone_id: number
  pickup_zone_name: string
  drop_address: string
  drop_zone_id: number
  drop_zone_name: string
  current_status: OrderStatus
  total_charge: string
  current_agent_id: number | null
  created_at: string
}

export type OrderPage = {
  items: OrderSummary[]
  page: number
  page_size: number
  total: number
  pages: number
}

export type OrderDetail = OrderSummary & {
  customer_id: number
  created_by_id: number
  pickup_postal_code: string
  pickup_latitude: string
  pickup_longitude: string
  drop_postal_code: string
  drop_latitude: string
  drop_longitude: string
  length_cm: string
  breadth_cm: string
  height_cm: string
  actual_weight_kg: string
  volumetric_weight_kg: string
  billable_weight_kg: string
  order_type: OrderType
  payment_type: PaymentType
  rate_card_id: number
  rate_per_kg: string
  delivery_charge: string
  cod_surcharge: string
  updated_at: string
}

export type TrackingHistoryEntry = {
  id: number
  from_status: OrderStatus | null
  to_status: OrderStatus
  actor_id: number
  actor_role: UserRole
  reason: string | null
  created_at: string
}

export type TrackingResponse = {
  order_id: number
  current_status: OrderStatus
  history: TrackingHistoryEntry[]
}

export class ApiError extends Error {
  status: number

  constructor(status: number, message: string) {
    super(message)
    this.name = 'ApiError'
    this.status = status
  }
}

type RequestOptions = {
  token?: string | null
  method?: string
  body?: unknown
  headers?: HeadersInit
}

async function request<T>(path: string, options: RequestOptions = {}): Promise<T> {
  const headers = new Headers(options.headers)

  if (options.body !== undefined && !headers.has('Content-Type')) {
    headers.set('Content-Type', 'application/json')
  }

  if (options.token) {
    headers.set('Authorization', `Bearer ${options.token}`)
  }

  const response = await fetch(`${apiBaseUrl}${path}`, {
    method: options.method ?? 'GET',
    headers,
    body:
      options.body === undefined
        ? undefined
        : typeof options.body === 'string' || options.body instanceof URLSearchParams
          ? options.body
          : JSON.stringify(options.body),
  })

  if (!response.ok) {
    throw new ApiError(response.status, await readError(response))
  }

  return response.json() as Promise<T>
}

async function readError(response: Response): Promise<string> {
  try {
    const data = (await response.json()) as { detail?: unknown }
    if (typeof data.detail === 'string') return data.detail
    if (Array.isArray(data.detail)) {
      return data.detail
        .map((item) => {
          if (typeof item === 'object' && item !== null && 'msg' in item) {
            return String((item as { msg: unknown }).msg)
          }
          return String(item)
        })
        .join(', ')
    }
  } catch {
    // Fall through to the status text below.
  }
  return response.statusText || 'Request failed'
}

export async function getHealth(): Promise<HealthResponse> {
  return request<HealthResponse>('/health')
}

export async function registerCustomer(payload: {
  name: string
  email: string
  phone: string
  password: string
}): Promise<User> {
  return request<User>('/auth/register', { method: 'POST', body: payload })
}

export async function login(email: string, password: string): Promise<TokenResponse> {
  const form = new URLSearchParams()
  form.set('username', email)
  form.set('password', password)

  return request<TokenResponse>('/auth/login', {
    method: 'POST',
    body: form,
    headers: { 'Content-Type': 'application/x-www-form-urlencoded' },
  })
}

export async function getMe(token: string): Promise<User> {
  return request<User>('/auth/me', { token })
}

export async function quoteOrder(
  token: string,
  payload: OrderInput,
): Promise<QuoteResponse> {
  return request<QuoteResponse>('/orders/quote', {
    method: 'POST',
    token,
    body: payload,
  })
}

export async function createOrder(
  token: string,
  payload: OrderInput,
): Promise<OrderDetail> {
  return request<OrderDetail>('/orders', { method: 'POST', token, body: payload })
}

export async function listOrders(
  token: string,
  page = 1,
  pageSize = 20,
): Promise<OrderPage> {
  return request<OrderPage>(`/orders?page=${page}&page_size=${pageSize}`, { token })
}

export async function getOrder(token: string, orderId: string): Promise<OrderDetail> {
  return request<OrderDetail>(`/orders/${orderId}`, { token })
}

export async function getTracking(
  token: string,
  orderId: string,
): Promise<TrackingResponse> {
  return request<TrackingResponse>(`/orders/${orderId}/tracking`, { token })
}

export async function rescheduleOrder(
  token: string,
  orderId: string,
  scheduledDate: string,
): Promise<OrderDetail> {
  return request<OrderDetail>(`/orders/${orderId}/reschedule`, {
    method: 'POST',
    token,
    body: { scheduled_date: scheduledDate },
  })
}
