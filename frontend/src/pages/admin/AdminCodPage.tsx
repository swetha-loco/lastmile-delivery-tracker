import { useEffect, useState } from 'react'

import type { CodSurcharge, OrderType } from '../../api/client'
import { ApiError, listCodSurcharges, putCodSurcharge } from '../../api/client'
import { Button } from '../../components/ui/Button'
import { FormField, TextInput } from '../../components/ui/FormField'
import { useAuth } from '../../lib/auth'
import { formatCurrency } from '../../lib/format'

const orderTypes: OrderType[] = ['B2C', 'B2B']

export default function AdminCodPage() {
  const { token } = useAuth()
  const [rows, setRows] = useState<CodSurcharge[]>([])
  const [drafts, setDrafts] = useState<Record<OrderType, { amount: string; is_active: boolean }>>({
    B2C: { amount: '', is_active: true },
    B2B: { amount: '', is_active: true },
  })
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  async function loadCod() {
    if (!token) return
    try {
      const nextRows = await listCodSurcharges(token)
      setRows(nextRows)
      setDrafts((current) => {
        const next = { ...current }
        nextRows.forEach((row) => {
          next[row.order_type] = { amount: row.amount, is_active: row.is_active }
        })
        return next
      })
      setError('')
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to load COD settings')
    }
  }

  useEffect(() => {
    void loadCod()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  async function save(orderType: OrderType) {
    if (!token) return
    try {
      const draft = drafts[orderType]
      await putCodSurcharge(token, orderType, draft)
      setNotice(`${orderType} COD surcharge saved.`)
      await loadCod()
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to save COD surcharge')
    }
  }

  const existing = (orderType: OrderType) => rows.find((row) => row.order_type === orderType)

  return (
    <div className="px-4 py-6 sm:px-8 lg:px-8">
      <div className="mx-auto max-w-5xl">
        <h1 className="text-3xl font-extrabold tracking-[-0.02em] text-[#071D34]">
          COD Settings
        </h1>
        <p className="mt-1 text-sm font-semibold text-[#667085]">
          Keep cash-on-delivery surcharges separate from rate-card pricing.
        </p>
        {error ? <Feedback tone="error" message={error} /> : null}
        {notice ? <Feedback tone="success" message={notice} /> : null}

        <div className="mt-6 grid gap-4 md:grid-cols-2">
          {orderTypes.map((orderType) => {
            const row = existing(orderType)
            const draft = drafts[orderType]
            return (
              <section
                key={orderType}
                className="rounded-xl border border-[#DDE5E1] bg-white p-5"
              >
                <div className="flex items-start justify-between gap-4">
                  <div>
                    <p className="text-xs font-extrabold uppercase tracking-[0.1em] text-[#667085]">
                      Order type
                    </p>
                    <h2 className="mt-1 text-2xl font-extrabold text-[#071D34]">
                      {orderType}
                    </h2>
                  </div>
                  <span
                    className={`rounded-md border px-2.5 py-1 text-xs font-extrabold uppercase ${
                      draft.is_active
                        ? 'border-[#BFE9DF] bg-[#DDF5EF] text-[#0F766E]'
                        : 'border-[#DDE5E1] bg-[#F7F8F6] text-[#667085]'
                    }`}
                  >
                    {draft.is_active ? 'Active' : 'Inactive'}
                  </span>
                </div>
                <p className="mt-4 text-sm font-semibold text-[#667085]">
                  Current surcharge:{' '}
                  <span className="font-extrabold text-[#142033]">
                    {row ? formatCurrency(row.amount) : 'Not configured'}
                  </span>
                </p>
                <div className="mt-5 grid gap-4">
                  <FormField label="Amount">
                    <TextInput
                      min="0"
                      step="0.01"
                      type="number"
                      value={draft.amount}
                      onChange={(event) =>
                        setDrafts((current) => ({
                          ...current,
                          [orderType]: { ...current[orderType], amount: event.target.value },
                        }))
                      }
                    />
                  </FormField>
                  <div className="flex flex-wrap gap-3">
                    <Button type="button" onClick={() => void save(orderType)}>
                      Save {orderType}
                    </Button>
                    <Button
                      type="button"
                      variant="secondary"
                      onClick={() =>
                        setDrafts((current) => ({
                          ...current,
                          [orderType]: {
                            ...current[orderType],
                            is_active: !current[orderType].is_active,
                          },
                        }))
                      }
                    >
                      {draft.is_active ? 'Mark inactive' : 'Mark active'}
                    </Button>
                  </div>
                </div>
              </section>
            )
          })}
        </div>
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
