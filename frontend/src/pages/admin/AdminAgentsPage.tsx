import { useEffect, useState } from 'react'

import type { AgentPublic } from '../../api/client'
import { ApiError, createAgent, listAgents } from '../../api/client'
import { Button } from '../../components/ui/Button'
import { FormField, TextInput } from '../../components/ui/FormField'
import { useAuth } from '../../lib/auth'
import { formatDateTime } from '../../lib/format'

const initialForm = { name: '', email: '', phone: '', password: '' }

export default function AdminAgentsPage() {
  const { token } = useAuth()
  const [agents, setAgents] = useState<AgentPublic[]>([])
  const [form, setForm] = useState(initialForm)
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')
  const [isLoading, setIsLoading] = useState(true)

  async function loadAgents() {
    if (!token) return
    setIsLoading(true)
    try {
      const page = await listAgents(token)
      setAgents(page.items)
      setError('')
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to load agents')
    } finally {
      setIsLoading(false)
    }
  }

  useEffect(() => {
    void loadAgents()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  async function handleCreate(event: React.FormEvent) {
    event.preventDefault()
    if (!token) return
    setError('')
    setNotice('')
    try {
      await createAgent(token, {
        name: form.name,
        email: form.email,
        phone: form.phone || undefined,
        password: form.password,
      })
      setForm(initialForm)
      setNotice('Delivery agent created.')
      await loadAgents()
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to create agent')
    }
  }

  return (
    <div className="px-4 py-6 sm:px-8 lg:px-8">
      <div className="mx-auto grid max-w-7xl gap-6 xl:grid-cols-[1fr_380px]">
        <section>
          <h1 className="text-3xl font-extrabold tracking-[-0.02em] text-[#071D34]">
            Agents
          </h1>
          <p className="mt-1 text-sm font-semibold text-[#667085]">
            Manage delivery-agent accounts and operational availability.
          </p>

          {error ? <Feedback tone="error" message={error} /> : null}
          {notice ? <Feedback tone="success" message={notice} /> : null}

          <div className="mt-6 overflow-hidden rounded-xl border border-[#DDE5E1] bg-white">
            <div className="grid grid-cols-[1.2fr_1fr_120px_120px_150px] gap-4 border-b border-[#DDE5E1] bg-[#F7F8F6] px-4 py-3 text-xs font-extrabold uppercase tracking-[0.08em] text-[#667085] max-lg:hidden">
              <span>Agent</span>
              <span>Contact</span>
              <span>Availability</span>
              <span>Zone</span>
              <span>Last assigned</span>
            </div>
            {isLoading ? (
              <div className="grid gap-2 p-4">
                {Array.from({ length: 4 }).map((_, index) => (
                  <div key={index} className="h-14 animate-pulse rounded-lg bg-[#F1F5F2]" />
                ))}
              </div>
            ) : agents.length ? (
              agents.map((agent) => (
                <div
                  key={agent.id}
                  className="grid gap-3 border-b border-[#DDE5E1] px-4 py-4 lg:grid-cols-[1.2fr_1fr_120px_120px_150px] lg:items-center"
                >
                  <div>
                    <p className="font-extrabold">{agent.name}</p>
                    <p className="text-sm font-semibold text-[#667085]">Agent #{agent.id}</p>
                  </div>
                  <div className="text-sm font-semibold text-[#667085]">
                    <p>{agent.email}</p>
                    <p>{agent.phone ?? 'No phone'}</p>
                  </div>
                  <AvailabilityBadge value={agent.availability} />
                  <p className="text-sm font-semibold text-[#667085]">
                    {agent.current_zone_id ? `Zone ${agent.current_zone_id}` : 'No zone'}
                  </p>
                  <p className="text-sm font-semibold text-[#667085]">
                    {agent.last_assigned_at ? formatDateTime(agent.last_assigned_at) : 'Never'}
                  </p>
                </div>
              ))
            ) : (
              <p className="p-8 text-center text-sm font-semibold text-[#667085]">
                No agents yet.
              </p>
            )}
          </div>
        </section>

        <aside className="rounded-xl border border-[#DDE5E1] bg-white p-5">
          <h2 className="text-xl font-extrabold text-[#142033]">Create agent</h2>
          <form className="mt-5 grid gap-4" onSubmit={handleCreate}>
            <FormField label="Name">
              <TextInput
                required
                value={form.name}
                onChange={(event) => setForm((current) => ({ ...current, name: event.target.value }))}
              />
            </FormField>
            <FormField label="Email">
              <TextInput
                required
                type="email"
                value={form.email}
                onChange={(event) => setForm((current) => ({ ...current, email: event.target.value }))}
              />
            </FormField>
            <FormField label="Phone">
              <TextInput
                value={form.phone}
                onChange={(event) => setForm((current) => ({ ...current, phone: event.target.value }))}
              />
            </FormField>
            <FormField label="Temporary password">
              <TextInput
                minLength={8}
                required
                type="password"
                value={form.password}
                onChange={(event) =>
                  setForm((current) => ({ ...current, password: event.target.value }))
                }
              />
            </FormField>
            <Button type="submit">Create delivery agent</Button>
          </form>
        </aside>
      </div>
    </div>
  )
}

export function AvailabilityBadge({ value }: { value: string }) {
  const tone =
    value === 'AVAILABLE'
      ? 'border-[#BFE9DF] bg-[#DDF5EF] text-[#0F766E]'
      : value === 'BUSY'
        ? 'border-[#F8D79B] bg-[#FFF2D8] text-[#A15C00]'
        : 'border-[#DDE5E1] bg-[#F7F8F6] text-[#667085]'
  return (
    <span className={`inline-flex rounded-md border px-2.5 py-1 text-xs font-extrabold ${tone}`}>
      {value}
    </span>
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
