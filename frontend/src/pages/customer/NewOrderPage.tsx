import { useState } from 'react'
import { useNavigate } from 'react-router'

import type {
  OrderCreateInput,
  OrderInput,
  OrderType,
  PaymentType,
  QuoteResponse,
} from '../../api/client'
import { ApiError, createOrder, quoteOrder } from '../../api/client'
import { PriceBreakdown } from '../../components/orders/PriceBreakdown'
import { RouteRail } from '../../components/orders/RouteRail'
import { Button } from '../../components/ui/Button'
import { FormField, SelectInput, TextArea, TextInput } from '../../components/ui/FormField'
import { Icon } from '../../components/ui/Icon'
import { useAuth } from '../../lib/auth'

const initialForm: OrderCreateInput = {
  pickup_address: '',
  drop_address: '',
  length_cm: '',
  breadth_cm: '',
  height_cm: '',
  actual_weight_kg: '',
  order_type: 'B2C',
  payment_type: 'PREPAID',
  package_description: '',
  is_fragile: false,
  delivery_instructions: '',
}

export default function NewOrderPage() {
  const { token } = useAuth()
  const navigate = useNavigate()
  const [form, setForm] = useState<OrderCreateInput>(initialForm)
  const [quote, setQuote] = useState<QuoteResponse | null>(null)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [isQuoting, setIsQuoting] = useState(false)
  const [isCreating, setIsCreating] = useState(false)

  function updateField<K extends keyof OrderCreateInput>(
    field: K,
    value: OrderCreateInput[K],
  ) {
    setQuote(null)
    setNotice('')
    setForm((current) => ({ ...current, [field]: value }))
  }

  function quotePayload(): OrderInput {
    return {
      pickup_address: form.pickup_address,
      drop_address: form.drop_address,
      length_cm: form.length_cm,
      breadth_cm: form.breadth_cm,
      height_cm: form.height_cm,
      actual_weight_kg: form.actual_weight_kg,
      order_type: form.order_type,
      payment_type: form.payment_type,
    }
  }

  async function handleQuote(event: React.FormEvent) {
    event.preventDefault()
    if (!token) return
    setError('')
    setNotice('')
    setIsQuoting(true)
    try {
      setQuote(await quoteOrder(token, quotePayload()))
      setNotice('Quote ready. Review the total before confirming your order.')
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to calculate quote')
    } finally {
      setIsQuoting(false)
    }
  }

  async function handleCreate() {
    if (!token) return
    setError('')
    setIsCreating(true)
    try {
      const order = await createOrder(token, form)
      navigate(`/orders/${order.id}`, {
        state: { flash: 'Order created. Your tracking timeline has started.' },
      })
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to create order')
    } finally {
      setIsCreating(false)
    }
  }

  return (
    <div className="px-4 py-6 sm:px-8 lg:px-10 lg:py-8">
      <div className="mx-auto max-w-7xl">
        <div className="mb-7">
          <p className="text-sm font-extrabold uppercase tracking-[0.12em] text-[#667085]">
            Create delivery
          </p>
          <h1 className="mt-2 text-3xl font-extrabold tracking-[-0.02em] text-[#071D34]">
            Quote before you confirm
          </h1>
        </div>

        <div className="grid min-w-0 gap-6 xl:grid-cols-[minmax(0,1fr)_420px]">
          <form
            className="rounded-2xl border border-[#DDE5E1] bg-white p-5 sm:p-6"
            onSubmit={handleQuote}
          >
            <div className="mb-6 flex items-center gap-3">
              <Step active label="Details" number="1" />
              <span className="h-px flex-1 bg-[#DDE5E1]" />
              <Step active={Boolean(quote)} label="Quote" number="2" />
              <span className="h-px flex-1 bg-[#DDE5E1]" />
              <Step active={false} label="Confirm" number="3" />
            </div>

            <section>
              <h2 className="text-lg font-extrabold text-[#142033]">Route details</h2>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <FormField label="Pickup address">
                  <TextInput
                    onChange={(event) => updateField('pickup_address', event.target.value)}
                    placeholder="Chennai GPO, 600001"
                    required
                    value={form.pickup_address}
                  />
                </FormField>
                <FormField label="Drop address">
                  <TextInput
                    onChange={(event) => updateField('drop_address', event.target.value)}
                    placeholder="Adyar, Chennai 600020"
                    required
                    value={form.drop_address}
                  />
                </FormField>
              </div>
            </section>

            <section className="mt-7">
              <h2 className="text-lg font-extrabold text-[#142033]">Package details</h2>
              <div className="mt-4 grid min-w-0 gap-4 sm:grid-cols-2 2xl:grid-cols-4">
                <FormField label="Length (cm)">
                  <TextInput
                    min="0.001"
                    onChange={(event) => updateField('length_cm', event.target.value)}
                    required
                    step="0.001"
                    type="number"
                    value={form.length_cm}
                  />
                </FormField>
                <FormField label="Breadth (cm)">
                  <TextInput
                    min="0.001"
                    onChange={(event) => updateField('breadth_cm', event.target.value)}
                    required
                    step="0.001"
                    type="number"
                    value={form.breadth_cm}
                  />
                </FormField>
                <FormField label="Height (cm)">
                  <TextInput
                    min="0.001"
                    onChange={(event) => updateField('height_cm', event.target.value)}
                    required
                    step="0.001"
                    type="number"
                    value={form.height_cm}
                  />
                </FormField>
                <FormField label="Actual weight (kg)">
                  <TextInput
                    min="0.001"
                    onChange={(event) => updateField('actual_weight_kg', event.target.value)}
                    required
                    step="0.001"
                    type="number"
                    value={form.actual_weight_kg}
                  />
                </FormField>
              </div>
            </section>

            <section className="mt-7">
              <div className="flex items-center gap-3">
                <span className="flex h-10 w-10 items-center justify-center rounded-lg bg-[#FFF2D8] text-[#D98613]">
                  <Icon name="box" className="h-5 w-5" />
                </span>
                <div>
                  <h2 className="text-lg font-extrabold text-[#142033]">
                    Package & handling
                  </h2>
                  <p className="text-sm font-semibold text-[#667085]">
                    Optional details for the operations team and delivery agent.
                  </p>
                </div>
              </div>
              <div className="mt-4 grid gap-4 md:grid-cols-2">
                <FormField label="Package description">
                  <TextInput
                    maxLength={200}
                    onChange={(event) =>
                      updateField('package_description', event.target.value)
                    }
                    placeholder="Laptop accessories, documents, books"
                    value={form.package_description ?? ''}
                  />
                </FormField>
                <label className="flex min-h-12 items-center gap-3 rounded-lg border border-[#DDE5E1] bg-[#F7F8F6] px-4 text-sm font-bold text-[#142033]">
                  <input
                    checked={Boolean(form.is_fragile)}
                    className="h-4 w-4 accent-[#F25F3A]"
                    onChange={(event) => updateField('is_fragile', event.target.checked)}
                    type="checkbox"
                  />
                  <span>
                    Fragile
                    <span className="block text-xs font-semibold text-[#667085]">
                      Handle this package with extra care
                    </span>
                  </span>
                </label>
              </div>
              <div className="mt-4">
                <FormField label="Delivery instructions">
                  <TextArea
                    maxLength={500}
                    onChange={(event) =>
                      updateField('delivery_instructions', event.target.value)
                    }
                    placeholder="Call before arrival, leave with building security, ring doorbell"
                    rows={3}
                    value={form.delivery_instructions ?? ''}
                  />
                </FormField>
              </div>
            </section>

            <section className="mt-7 grid gap-4 md:grid-cols-2">
              <FormField label="Order type">
                <SelectInput
                  onChange={(event) =>
                    updateField('order_type', event.target.value as OrderType)
                  }
                  value={form.order_type}
                >
                  <option value="B2C">B2C</option>
                  <option value="B2B">B2B</option>
                </SelectInput>
              </FormField>
              <FormField label="Payment type">
                <SelectInput
                  onChange={(event) =>
                    updateField('payment_type', event.target.value as PaymentType)
                  }
                  value={form.payment_type}
                >
                  <option value="PREPAID">Prepaid</option>
                  <option value="COD">Cash on delivery</option>
                </SelectInput>
              </FormField>
            </section>

            {error ? (
              <p className="mt-5 rounded-lg border border-[#F1B5B5] bg-[#FDE7E7] p-4 text-sm font-bold text-[#B42318]">
                {error}
              </p>
            ) : null}
            {notice ? (
              <p className="mt-5 rounded-lg border border-[#BFE9DF] bg-[#DDF5EF] p-4 text-sm font-bold text-[#0F766E]">
                {notice}
              </p>
            ) : null}

            <div className="mt-7 flex flex-wrap gap-3">
              <Button disabled={isQuoting} type="submit">
                <Icon name="route" className="h-4 w-4" />
                {isQuoting ? 'Calculating...' : 'Get quote'}
              </Button>
              {quote ? (
                <Button disabled={isCreating} type="button" onClick={handleCreate}>
                  {isCreating ? 'Confirming...' : 'Confirm order'}
                </Button>
              ) : null}
            </div>
          </form>

          <aside className="grid min-w-0 content-start gap-5">
            {quote ? (
              <div className="grid min-w-0 gap-5 animate-in">
                <RouteRail
                  drop={quote.drop.formatted_address}
                  dropZone={quote.drop.zone_name}
                  pickup={quote.pickup.formatted_address}
                  pickupZone={quote.pickup.zone_name}
                />
                <PriceBreakdown
                  actualWeight={quote.actual_weight_kg}
                  billableWeight={quote.billable_weight_kg}
                  codSurcharge={quote.cod_surcharge}
                  deliveryCharge={quote.delivery_charge}
                  destinationZone={quote.drop.zone_name}
                  orderType={quote.order_type}
                  originZone={quote.pickup.zone_name}
                  ratePerKg={quote.rate_per_kg}
                  totalCharge={quote.total_charge}
                  volumetricWeight={quote.volumetric_weight_kg}
                />
              </div>
            ) : (
              <div className="rounded-2xl border border-dashed border-[#C9D6D1] bg-white p-6">
                <div className="flex h-12 w-12 items-center justify-center rounded-xl bg-[#FFF2D8] text-[#D98613]">
                  <Icon name="box" className="h-6 w-6" />
                </div>
                <h2 className="mt-5 text-xl font-extrabold text-[#142033]">
                  Quote appears here
                </h2>
                <p className="mt-2 text-sm font-semibold leading-6 text-[#667085]">
                  The pricing rail will show actual, volumetric, and billable weight,
                  followed by rate, COD surcharge, and total charge.
                </p>
              </div>
            )}
          </aside>
        </div>
      </div>
    </div>
  )
}

function Step({
  active,
  label,
  number,
}: {
  active: boolean
  label: string
  number: string
}) {
  return (
    <div className="flex items-center gap-2">
      <span
        className={`flex h-8 w-8 items-center justify-center rounded-full text-sm font-extrabold ${
          active ? 'bg-[#F25F3A] text-white' : 'bg-[#F1F5F2] text-[#667085]'
        }`}
      >
        {number}
      </span>
      <span className="hidden text-sm font-extrabold text-[#667085] sm:block">{label}</span>
    </div>
  )
}
