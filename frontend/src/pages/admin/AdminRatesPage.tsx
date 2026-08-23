import { useEffect, useState } from 'react'

import type { OrderType, RateCard, Zone } from '../../api/client'
import {
  ApiError,
  createRateCard,
  listRateCards,
  listZones,
  updateRateCard,
} from '../../api/client'
import { Button } from '../../components/ui/Button'
import { FormField, SelectInput, TextInput } from '../../components/ui/FormField'
import { useAuth } from '../../lib/auth'
import { formatCurrency } from '../../lib/format'

const initialForm = {
  origin_zone_id: '',
  destination_zone_id: '',
  order_type: 'B2C' as OrderType,
  rate_per_kg: '',
}

export default function AdminRatesPage() {
  const { token } = useAuth()
  const [zones, setZones] = useState<Zone[]>([])
  const [rates, setRates] = useState<RateCard[]>([])
  const [form, setForm] = useState(initialForm)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const zoneName = (id: number) => zones.find((zone) => zone.id === id)?.name ?? `Zone ${id}`

  async function loadRates() {
    if (!token) return
    try {
      const [zoneRows, rateRows] = await Promise.all([listZones(token), listRateCards(token)])
      setZones(zoneRows)
      setRates(rateRows)
      setError('')
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to load rate cards')
    }
  }

  useEffect(() => {
    void loadRates()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  async function submitRate(event: React.FormEvent) {
    event.preventDefault()
    if (!token) return
    try {
      await createRateCard(token, {
        origin_zone_id: Number(form.origin_zone_id),
        destination_zone_id: Number(form.destination_zone_id),
        order_type: form.order_type,
        rate_per_kg: form.rate_per_kg,
      })
      setForm(initialForm)
      setNotice('Rate card created.')
      await loadRates()
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to create rate card')
    }
  }

  async function toggleRate(rate: RateCard) {
    if (!token) return
    await updateRateCard(token, rate.id, { is_active: !rate.is_active })
    await loadRates()
  }

  return (
    <div className="px-4 py-6 sm:px-8 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <h1 className="text-3xl font-extrabold tracking-[-0.02em] text-[#071D34]">
          Rate Cards
        </h1>
        <p className="mt-1 text-sm font-semibold text-[#667085]">
          Configure per-kg B2B/B2C pricing by origin and destination zone.
        </p>
        {error ? <Feedback tone="error" message={error} /> : null}
        {notice ? <Feedback tone="success" message={notice} /> : null}

        <section className="mt-6 rounded-xl border border-[#DDE5E1] bg-white p-5">
          <form className="grid gap-4 md:grid-cols-[1fr_1fr_140px_140px_auto]" onSubmit={submitRate}>
            <FormField label="Origin zone">
              <SelectInput
                required
                value={form.origin_zone_id}
                onChange={(event) =>
                  setForm((current) => ({ ...current, origin_zone_id: event.target.value }))
                }
              >
                <option value="">Choose</option>
                {zones.map((zone) => (
                  <option key={zone.id} value={zone.id}>
                    {zone.name}
                  </option>
                ))}
              </SelectInput>
            </FormField>
            <FormField label="Destination zone">
              <SelectInput
                required
                value={form.destination_zone_id}
                onChange={(event) =>
                  setForm((current) => ({ ...current, destination_zone_id: event.target.value }))
                }
              >
                <option value="">Choose</option>
                {zones.map((zone) => (
                  <option key={zone.id} value={zone.id}>
                    {zone.name}
                  </option>
                ))}
              </SelectInput>
            </FormField>
            <FormField label="Type">
              <SelectInput
                value={form.order_type}
                onChange={(event) =>
                  setForm((current) => ({ ...current, order_type: event.target.value as OrderType }))
                }
              >
                <option value="B2C">B2C</option>
                <option value="B2B">B2B</option>
              </SelectInput>
            </FormField>
            <FormField label="Rate/kg">
              <TextInput
                min="0.01"
                required
                step="0.01"
                type="number"
                value={form.rate_per_kg}
                onChange={(event) =>
                  setForm((current) => ({ ...current, rate_per_kg: event.target.value }))
                }
              />
            </FormField>
            <Button className="self-end" type="submit">
              Add rate
            </Button>
          </form>
        </section>

        <section className="mt-6 overflow-hidden rounded-xl border border-[#DDE5E1] bg-white">
          <div className="grid grid-cols-[1fr_1fr_110px_130px_120px_110px] gap-4 border-b border-[#DDE5E1] bg-[#F7F8F6] px-4 py-3 text-xs font-extrabold uppercase tracking-[0.08em] text-[#667085] max-lg:hidden">
            <span>Origin</span>
            <span>Destination</span>
            <span>Type</span>
            <span>Mode</span>
            <span>Rate/kg</span>
            <span>Status</span>
          </div>
          {rates.map((rate) => (
            <div
              key={rate.id}
              className="grid gap-3 border-b border-[#DDE5E1] px-4 py-4 lg:grid-cols-[1fr_1fr_110px_130px_120px_110px] lg:items-center"
            >
              <p className="font-extrabold">{zoneName(rate.origin_zone_id)}</p>
              <p className="font-extrabold">{zoneName(rate.destination_zone_id)}</p>
              <p className="text-sm font-extrabold text-[#667085]">{rate.order_type}</p>
              <p className="text-sm font-semibold text-[#667085]">
                {rate.origin_zone_id === rate.destination_zone_id ? 'Intra-zone' : 'Inter-zone'}
              </p>
              <p className="font-extrabold">{formatCurrency(rate.rate_per_kg)}</p>
              <Button type="button" variant="secondary" onClick={() => void toggleRate(rate)}>
                {rate.is_active ? 'Active' : 'Inactive'}
              </Button>
            </div>
          ))}
        </section>
      </div>
    </div>
  )
}

function Feedback({ tone, message }: { tone: 'error' | 'success'; message: string }) {
  return (
    <p
      className={`mt-4 rounded-lg border p-3 text-sm font-bold ${
        tone === 'success'
          ? 'border-[#BFE9DF] bg-[#DDF5EF] text-[#0F766E]'
          : 'border-[#F1B5B5] bg-[#FDE7E7] text-[#B42318]'
      }`}
    >
      {message}
    </p>
  )
}
