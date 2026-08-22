import { Icon } from '../ui/Icon'

export function RouteRail({
  pickup,
  pickupZone,
  drop,
  dropZone,
  spacious = false,
}: {
  pickup: string
  pickupZone?: string
  drop: string
  dropZone?: string
  spacious?: boolean
}) {
  return (
    <div className={`route-panel ${spacious ? 'min-h-44 content-center' : ''}`}>
      <div
        className={`grid gap-5 sm:grid-cols-[1fr_auto_1fr] sm:items-center ${
          spacious ? 'min-h-32' : ''
        }`}
      >
        <RouteStop tone="pickup" label="Pickup" address={pickup} zone={pickupZone} />
        <div className="hidden items-center gap-2 text-[#128C7E] sm:flex">
          <span className={`${spacious ? 'w-24' : 'w-12'} h-px bg-[#9BD9CC]`} />
          <span className="flex h-11 w-11 items-center justify-center rounded-full border border-[#BFE9DF] bg-white text-[#128C7E] shadow-sm">
            <Icon name="arrow" className="h-5 w-5" />
          </span>
          <span className={`${spacious ? 'w-24' : 'w-12'} h-px bg-[#9BD9CC]`} />
        </div>
        <RouteStop tone="drop" label="Drop" address={drop} zone={dropZone} />
      </div>
    </div>
  )
}

function RouteStop({
  tone,
  label,
  address,
  zone,
}: {
  tone: 'pickup' | 'drop'
  label: string
  address: string
  zone?: string
}) {
  return (
    <div className="flex gap-3">
      <span
        className={`mt-1 flex h-9 w-9 shrink-0 items-center justify-center rounded-full ${
          tone === 'pickup'
            ? 'bg-[#DDF5EF] text-[#128C7E]'
            : 'bg-[#FDE7E7] text-[#D64545]'
        }`}
      >
        <Icon name="pin" className="h-5 w-5" />
      </span>
      <div>
        <p className="text-xs font-extrabold uppercase tracking-[0.09em] text-[#667085]">
          {label}
        </p>
        <p className="mt-1 line-clamp-2 text-base font-extrabold text-[#142033]">
          {address}
        </p>
        {zone ? <p className="mt-1 text-sm font-semibold text-[#667085]">{zone}</p> : null}
      </div>
    </div>
  )
}
