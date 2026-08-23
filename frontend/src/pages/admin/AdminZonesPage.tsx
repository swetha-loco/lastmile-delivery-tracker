import { useEffect, useMemo, useState } from 'react'

import type { Area, Zone } from '../../api/client'
import { ApiError, createArea, createZone, listAreas, listZones, updateArea, updateZone } from '../../api/client'
import { Button } from '../../components/ui/Button'
import { FormField, SelectInput, TextInput } from '../../components/ui/FormField'
import { useAuth } from '../../lib/auth'

export default function AdminZonesPage() {
  const { token } = useAuth()
  const [zones, setZones] = useState<Zone[]>([])
  const [areas, setAreas] = useState<Area[]>([])
  const [selectedZoneId, setSelectedZoneId] = useState<number | null>(null)
  const [zoneName, setZoneName] = useState('')
  const [areaForm, setAreaForm] = useState({ name: '', postal_code: '' })
  const [error, setError] = useState('')
  const [notice, setNotice] = useState('')

  const selectedZone = zones.find((zone) => zone.id === selectedZoneId) ?? zones[0]
  const visibleAreas = useMemo(
    () => areas.filter((area) => !selectedZone || area.zone_id === selectedZone.id),
    [areas, selectedZone],
  )

  async function loadConfig() {
    if (!token) return
    try {
      const [zoneRows, areaRows] = await Promise.all([listZones(token), listAreas(token)])
      setZones(zoneRows)
      setAreas(areaRows)
      setSelectedZoneId((current) => current ?? zoneRows[0]?.id ?? null)
      setError('')
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to load zones')
    }
  }

  useEffect(() => {
    void loadConfig()
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [token])

  async function submitZone(event: React.FormEvent) {
    event.preventDefault()
    if (!token) return
    try {
      await createZone(token, { name: zoneName })
      setZoneName('')
      setNotice('Zone created.')
      await loadConfig()
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to create zone')
    }
  }

  async function submitArea(event: React.FormEvent) {
    event.preventDefault()
    if (!token || !selectedZone) return
    try {
      await createArea(token, { ...areaForm, zone_id: selectedZone.id })
      setAreaForm({ name: '', postal_code: '' })
      setNotice('Area created.')
      await loadConfig()
    } catch (exc) {
      setError(exc instanceof ApiError ? exc.message : 'Unable to create area')
    }
  }

  async function toggleZone(zone: Zone) {
    if (!token) return
    await updateZone(token, zone.id, { is_active: !zone.is_active })
    await loadConfig()
  }

  async function toggleArea(area: Area) {
    if (!token) return
    await updateArea(token, area.id, { is_active: !area.is_active })
    await loadConfig()
  }

  return (
    <div className="px-4 py-6 sm:px-8 lg:px-8">
      <div className="mx-auto max-w-7xl">
        <h1 className="text-3xl font-extrabold tracking-[-0.02em] text-[#071D34]">
          Zones & Areas
        </h1>
        <p className="mt-1 text-sm font-semibold text-[#667085]">
          Configure supported service areas by postal code.
        </p>
        {error ? <Feedback tone="error" message={error} /> : null}
        {notice ? <Feedback tone="success" message={notice} /> : null}

        <div className="mt-6 grid gap-6 lg:grid-cols-[360px_1fr]">
          <section className="rounded-xl border border-[#DDE5E1] bg-white p-5">
            <h2 className="text-lg font-extrabold">Zones</h2>
            <form className="mt-4 flex gap-2" onSubmit={submitZone}>
              <TextInput
                required
                placeholder="New zone"
                value={zoneName}
                onChange={(event) => setZoneName(event.target.value)}
              />
              <Button type="submit">Add</Button>
            </form>
            <div className="mt-5 grid gap-2">
              {zones.map((zone) => (
                <button
                  key={zone.id}
                  className={`flex items-center justify-between rounded-lg border px-3 py-3 text-left ${
                    selectedZone?.id === zone.id
                      ? 'border-[#128C7E] bg-[#DDF5EF]'
                      : 'border-[#DDE5E1] bg-white'
                  }`}
                  type="button"
                  onClick={() => setSelectedZoneId(zone.id)}
                >
                  <span>
                    <span className="block font-extrabold">{zone.name}</span>
                    <span className="text-xs font-semibold text-[#667085]">
                      {zone.is_active ? 'Active' : 'Inactive'}
                    </span>
                  </span>
                  <span
                    className="text-xs font-extrabold text-[#F25F3A]"
                    onClick={(event) => {
                      event.stopPropagation()
                      void toggleZone(zone)
                    }}
                  >
                    {zone.is_active ? 'Disable' : 'Enable'}
                  </span>
                </button>
              ))}
            </div>
          </section>

          <section className="rounded-xl border border-[#DDE5E1] bg-white p-5">
            <div className="flex flex-wrap items-start justify-between gap-4">
              <div>
                <h2 className="text-lg font-extrabold">
                  Areas {selectedZone ? `for ${selectedZone.name}` : ''}
                </h2>
                <p className="text-sm font-semibold text-[#667085]">
                  Postal codes remain strings and are never guessed.
                </p>
              </div>
            </div>
            {selectedZone ? (
              <form className="mt-5 grid gap-3 md:grid-cols-[1fr_160px_auto]" onSubmit={submitArea}>
                <FormField label="Area name">
                  <TextInput
                    required
                    value={areaForm.name}
                    onChange={(event) =>
                      setAreaForm((current) => ({ ...current, name: event.target.value }))
                    }
                  />
                </FormField>
                <FormField label="Postal code">
                  <TextInput
                    required
                    value={areaForm.postal_code}
                    onChange={(event) =>
                      setAreaForm((current) => ({ ...current, postal_code: event.target.value }))
                    }
                  />
                </FormField>
                <Button className="self-end" type="submit">
                  Add area
                </Button>
              </form>
            ) : null}
            <div className="mt-5 overflow-hidden rounded-lg border border-[#DDE5E1]">
              {visibleAreas.map((area) => (
                <div
                  key={area.id}
                  className="grid gap-2 border-b border-[#DDE5E1] px-4 py-3 md:grid-cols-[1fr_140px_120px] md:items-center"
                >
                  <div>
                    <p className="font-extrabold">{area.name}</p>
                    <p className="text-sm font-semibold text-[#667085]">{area.postal_code}</p>
                  </div>
                  <SelectInput
                    value={area.zone_id}
                    onChange={(event) =>
                      token &&
                      updateArea(token, area.id, { zone_id: Number(event.target.value) }).then(
                        loadConfig,
                      )
                    }
                  >
                    {zones.map((zone) => (
                      <option key={zone.id} value={zone.id}>
                        {zone.name}
                      </option>
                    ))}
                  </SelectInput>
                  <Button type="button" variant="secondary" onClick={() => void toggleArea(area)}>
                    {area.is_active ? 'Active' : 'Inactive'}
                  </Button>
                </div>
              ))}
              {!visibleAreas.length ? (
                <p className="p-6 text-center text-sm font-semibold text-[#667085]">
                  No areas for this zone yet.
                </p>
              ) : null}
            </div>
          </section>
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
