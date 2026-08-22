from dataclasses import dataclass
from decimal import Decimal, ROUND_HALF_UP

from app.models import CodSurcharge, PaymentType, RateCard

WEIGHT_QUANTUM = Decimal("0.001")
MONEY_QUANTUM = Decimal("0.01")
VOLUMETRIC_DIVISOR = Decimal("5000")


@dataclass(frozen=True)
class PriceBreakdown:
    rate_card_id: int
    actual_weight_kg: Decimal
    volumetric_weight_kg: Decimal
    billable_weight_kg: Decimal
    rate_per_kg: Decimal
    delivery_charge: Decimal
    cod_surcharge: Decimal
    total_charge: Decimal


def calculate_price(
    *,
    length_cm: Decimal,
    breadth_cm: Decimal,
    height_cm: Decimal,
    actual_weight_kg: Decimal,
    payment_type: PaymentType,
    rate_card: RateCard,
    cod_surcharge: CodSurcharge | None,
) -> PriceBreakdown:
    actual_weight = quantize_weight(actual_weight_kg)
    volumetric_weight = quantize_weight(
        length_cm * breadth_cm * height_cm / VOLUMETRIC_DIVISOR
    )
    billable_weight = max(actual_weight, volumetric_weight)
    delivery_charge = quantize_money(billable_weight * rate_card.rate_per_kg)
    surcharge = Decimal("0.00")
    if payment_type == PaymentType.COD:
        if cod_surcharge is None:
            raise MissingCodSurchargeError
        surcharge = quantize_money(cod_surcharge.amount)
    total_charge = quantize_money(delivery_charge + surcharge)
    return PriceBreakdown(
        rate_card_id=rate_card.id,
        actual_weight_kg=actual_weight,
        volumetric_weight_kg=volumetric_weight,
        billable_weight_kg=billable_weight,
        rate_per_kg=quantize_money(rate_card.rate_per_kg),
        delivery_charge=delivery_charge,
        cod_surcharge=surcharge,
        total_charge=total_charge,
    )


def quantize_weight(value: Decimal) -> Decimal:
    return value.quantize(WEIGHT_QUANTUM, rounding=ROUND_HALF_UP)


def quantize_money(value: Decimal) -> Decimal:
    return value.quantize(MONEY_QUANTUM, rounding=ROUND_HALF_UP)


class MissingCodSurchargeError(Exception):
    pass
