from decimal import Decimal, ROUND_HALF_UP

TWO = Decimal("0.01")
ZERO = Decimal("0.00")

def nz_decimal(value):
    """
    Convierte a Decimal con 2 decimales, evitando None/NaN/strings raros/negativos.
    """
    try:
        d = Decimal(str(value))
        if d < ZERO:
            d = ZERO
        return d.quantize(TWO, rounding=ROUND_HALF_UP)
    except Exception:
        return ZERO

def clamp_non_negative(d: Decimal) -> Decimal:
    return d if d >= ZERO else ZERO
