const apiBaseUrl = (import.meta.env.VITE_API_URL ?? '').replace(/\/+$/, '')

export type UserRole = 'CUSTOMER' | 'DELIVERY_AGENT' | 'ADMIN'
export type OrderType = 'B2B' | 'B2C'
export type PaymentType = 'PREPAID' | 'COD'
export type AgentAvailability = 'AVAILABLE' | 'BUSY' | 'OFFLINE'
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

export type PageQuery = {
  page?: number
  pageSize?: number
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

export type AgentPublic = {
  id: number
  name: string
  email: string
  phone: string | null
  availability: AgentAvailability
  current_zone_id: number | null
  current_latitude: string | null
  current_longitude: string | null
  location_updated_at: string | null
  last_assigned_at: string | null
}

export type AgentPage = {
  items: AgentPublic[]
  page: number
  page_size: number
  total: number
  pages: number
}

export type AgentProfile = {
  user_id: number
  availability: AgentAvailability
  current_latitude: string | null
  current_longitude: string | null
  current_zone_id: number | null
  location_updated_at: string | null
  last_assigned_at: string | null
}

export type Zone = {
  id: number
  name: string
  is_active: boolean
}

export type Area = {
  id: number
  name: string
  postal_code: string
  zone_id: number
  is_active: boolean
}

export type RateCard = {
  id: number
  origin_zone_id: number
  destination_zone_id: number
  order_type: OrderType
  rate_per_kg: string
  is_active: boolean
}

export type CodSurcharge = {
  id: number
  order_type: OrderType
  amount: string
  is_active: boolean
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

export async function listAdminOrders(
  token: string,
  filters: {
    page?: number
    pageSize?: number
    status?: string
    zoneId?: string
    agentId?: string
  } = {},
): Promise<OrderPage> {
  const params = new URLSearchParams()
  params.set('page', String(filters.page ?? 1))
  params.set('page_size', String(filters.pageSize ?? 20))
  if (filters.status) params.set('status', filters.status)
  if (filters.zoneId) params.set('zone_id', filters.zoneId)
  if (filters.agentId) params.set('agent_id', filters.agentId)
  return request<OrderPage>(`/admin/orders?${params.toString()}`, { token })
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

export async function listAgents(
  token: string,
  page = 1,
  pageSize = 100,
): Promise<AgentPage> {
  return request<AgentPage>(`/admin/agents?page=${page}&page_size=${pageSize}`, { token })
}

export async function createAgent(
  token: string,
  payload: { name: string; email: string; phone?: string; password: string },
): Promise<User> {
  return request<User>('/admin/agents', { method: 'POST', token, body: payload })
}

export async function assignOrder(
  token: string,
  orderId: number,
  agentId: number,
): Promise<OrderDetail> {
  return request<OrderDetail>(`/admin/orders/${orderId}/assign`, {
    method: 'POST',
    token,
    body: { agent_id: agentId },
  })
}

export async function autoAssignOrder(
  token: string,
  orderId: number,
): Promise<OrderDetail> {
  return request<OrderDetail>(`/admin/orders/${orderId}/auto-assign`, {
    method: 'POST',
    token,
  })
}

export async function overrideOrderStatus(
  token: string,
  orderId: number,
  targetStatus: OrderStatus,
  reason: string,
): Promise<OrderDetail> {
  return request<OrderDetail>(`/admin/orders/${orderId}/override-status`, {
    method: 'POST',
    token,
    body: { target_status: targetStatus, reason },
  })
}

export async function listZones(token: string): Promise<Zone[]> {
  return request<Zone[]>('/admin/zones', { token })
}

export async function createZone(
  token: string,
  payload: { name: string; is_active?: boolean },
): Promise<Zone> {
  return request<Zone>('/admin/zones', { method: 'POST', token, body: payload })
}

export async function updateZone(
  token: string,
  zoneId: number,
  payload: Partial<Pick<Zone, 'name' | 'is_active'>>,
): Promise<Zone> {
  return request<Zone>(`/admin/zones/${zoneId}`, { method: 'PATCH', token, body: payload })
}

export async function listAreas(token: string, zoneId?: number): Promise<Area[]> {
  return request<Area[]>(`/admin/areas${zoneId ? `?zone_id=${zoneId}` : ''}`, { token })
}

export async function createArea(
  token: string,
  payload: { name: string; postal_code: string; zone_id: number; is_active?: boolean },
): Promise<Area> {
  return request<Area>('/admin/areas', { method: 'POST', token, body: payload })
}

export async function updateArea(
  token: string,
  areaId: number,
  payload: Partial<Pick<Area, 'name' | 'postal_code' | 'zone_id' | 'is_active'>>,
): Promise<Area> {
  return request<Area>(`/admin/areas/${areaId}`, { method: 'PATCH', token, body: payload })
}

export async function listRateCards(
  token: string,
  filters: { originZoneId?: string; destinationZoneId?: string; orderType?: string } = {},
): Promise<RateCard[]> {
  const params = new URLSearchParams()
  if (filters.originZoneId) params.set('origin_zone_id', filters.originZoneId)
  if (filters.destinationZoneId) params.set('destination_zone_id', filters.destinationZoneId)
  if (filters.orderType) params.set('order_type', filters.orderType)
  const query = params.toString()
  return request<RateCard[]>(`/admin/rate-cards${query ? `?${query}` : ''}`, { token })
}

export async function createRateCard(
  token: string,
  payload: {
    origin_zone_id: number
    destination_zone_id: number
    order_type: OrderType
    rate_per_kg: string
    is_active?: boolean
  },
): Promise<RateCard> {
  return request<RateCard>('/admin/rate-cards', { method: 'POST', token, body: payload })
}

export async function updateRateCard(
  token: string,
  rateCardId: number,
  payload: { rate_per_kg?: string; is_active?: boolean },
): Promise<RateCard> {
  return request<RateCard>(`/admin/rate-cards/${rateCardId}`, {
    method: 'PATCH',
    token,
    body: payload,
  })
}

export async function listCodSurcharges(token: string): Promise<CodSurcharge[]> {
  return request<CodSurcharge[]>('/admin/cod-surcharges', { token })
}

export async function putCodSurcharge(
  token: string,
  orderType: OrderType,
  payload: { amount: string; is_active: boolean },
): Promise<CodSurcharge> {
  return request<CodSurcharge>(`/admin/cod-surcharges/${orderType}`, {
    method: 'PUT',
    token,
    body: payload,
  })
}

export async function listAgentOrders(
  token: string,
  page = 1,
  pageSize = 20,
): Promise<OrderPage> {
  return request<OrderPage>(`/agent/orders?page=${page}&page_size=${pageSize}`, { token })
}

export async function getAgentProfile(token: string): Promise<AgentProfile> {
  return request<AgentProfile>('/agent/profile', { token })
}

export async function updateAgentAvailability(
  token: string,
  availability: Exclude<AgentAvailability, 'BUSY'>,
): Promise<AgentProfile> {
  return request<AgentProfile>('/agent/availability', {
    method: 'PATCH',
    token,
    body: { availability },
  })
}

export async function updateAgentLocation(
  token: string,
  latitude: number,
  longitude: number,
): Promise<AgentProfile> {
  return request<AgentProfile>('/agent/location', {
    method: 'PATCH',
    token,
    body: { latitude, longitude },
  })
}

export async function updateAgentOrderStatus(
  token: string,
  orderId: number,
  targetStatus: OrderStatus,
  reason?: string,
): Promise<OrderDetail> {
  return request<OrderDetail>(`/agent/orders/${orderId}/status`, {
    method: 'PATCH',
    token,
    body: { target_status: targetStatus, reason },
  })
}
