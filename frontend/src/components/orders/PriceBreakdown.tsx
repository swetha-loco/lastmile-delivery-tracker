import { formatCurrency } from '../../lib/format'

export function PriceBreakdown({
  actualWeight,
  volumetricWeight,
  billableWeight,
  originZone,
  destinationZone,
  orderType,
  ratePerKg,
  deliveryCharge,
  codSurcharge,
  totalCharge,
}: {
  actualWeight: string
  volumetricWeight: string
  billableWeight: string
  originZone?: string
  destinationZone?: string
  orderType?: string
  ratePerKg: string
  deliveryCharge: string
  codSurcharge: string
  totalCharge: string
}) {
  const actual = Number(actualWeight)
  const volumetric = Number(volumetricWeight)
  const billableReason =
    actual === volumetric
      ? 'Actual and volumetric weight are equal, so that weight is used for billing.'
      : actual > volumetric
        ? 'Actual weight is higher than volumetric weight, so actual weight is used for billing.'
        : 'Volumetric weight is higher than actual weight, so volumetric weight is used for billing.'
  const routeLabel =
    originZone && destinationZone
      ? `${originZone} -> ${destinationZone}${orderType ? ` / ${orderType}` : ''}`
      : orderType
        ? `${orderType} rate`
        : 'Configured rate'

  return (
    <div className="rounded-xl border border-[#DDE5E1] bg-white p-5">
      <p className="text-xs font-extrabold uppercase tracking-[0.1em] text-[#667085]">
        Price Breakdown
      </p>
      <div className="mt-5 grid gap-3">
        <WeightLine label="Actual weight" value={`${actualWeight} kg`} />
        <WeightLine label="Volumetric weight" value={`${volumetricWeight} kg`} />
        <div className="rounded-lg border border-[#BFE9DF] bg-[#DDF5EF] p-3">
          <div className="flex items-center justify-between gap-4">
            <span className="text-sm font-extrabold text-[#0F766E]">Billable weight</span>
            <span className="font-extrabold text-[#0F766E]">{billableWeight} kg</span>
          </div>
          <p className="mt-2 text-xs font-semibold leading-5 text-[#0F766E]">
            {billableReason}
          </p>
        </div>
      </div>

      <div className="mt-5 border-t border-[#DDE5E1] pt-4">
        <p className="mb-2 text-xs font-extrabold uppercase tracking-[0.08em] text-[#667085]">
          {routeLabel}
        </p>
        <WeightLine label="Rate per kg" value={formatCurrency(ratePerKg)} />
        <WeightLine
          label={`Delivery charge (${billableWeight} kg x ${formatCurrency(ratePerKg)})`}
          value={formatCurrency(deliveryCharge)}
        />
        <WeightLine label="COD surcharge" value={formatCurrency(codSurcharge)} />
      </div>

      <div className="mt-4 flex items-end justify-between rounded-lg bg-[#071D34] p-4 text-white">
        <span className="text-sm font-bold text-white/75">Total before confirmation</span>
        <span className="text-2xl font-extrabold">{formatCurrency(totalCharge)}</span>
      </div>
    </div>
  )
}

function WeightLine({ label, value }: { label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4 py-1 text-sm">
      <span className="font-semibold text-[#667085]">{label}</span>
      <span className="font-extrabold text-[#142033]">{value}</span>
    </div>
  )
}
