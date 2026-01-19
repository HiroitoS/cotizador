from decimal import Decimal, ROUND_HALF_UP
from .utils import nz_decimal, clamp_non_negative

TWO = Decimal("0.01")
HUNDRED = Decimal("100")


def q2(x: Decimal) -> Decimal:
    return Decimal(x).quantize(TWO, rounding=ROUND_HALF_UP)


def normalize_percent(value) -> Decimal:
    """
    Acepta:
    - 0.36  (ya fracción)
    - 36    (porcentaje)
    - "36%" (texto)
    Devuelve fracción: 0.36
    """
    if value is None:
        return Decimal("0")

    if isinstance(value, str):
        v = value.strip().replace("%", "")
        try:
            value = Decimal(v)
        except Exception:
            return Decimal("0")

    val = nz_decimal(value)

    # Si viene 36 => 0.36
    if val > 1:
        val = val / HUNDRED

    # clamp razonable
    if val < 0:
        val = Decimal("0")
    if val > 1:
        val = Decimal("1")

    return val


def calcular_item(tipo_venta: str, producto, data: dict) -> dict:
    """
    Fuente única de verdad para cálculos.
    Replica lógica Excel:
    precio_proveedor = pvp - (pvp * descuento_proveedor)
    donde descuento_proveedor es porcentaje (36% / 40%) pero en excel se ve como 0.36/0.40.
    """

    tipo_venta = (tipo_venta or "").upper().strip()
    if tipo_venta == "PV":
        tipo_venta = "PUNTO_DE_VENTA"

    precio_be = nz_decimal(data.get("precio_be", getattr(producto, "pvp_2026", 0)))
    descuento_ie = nz_decimal(data.get("descuento_ie", 20))  # tu sistema hoy lo usa como %
    precio_ppff = nz_decimal(data.get("precio_ppff", 0))
    comi_coo = nz_decimal(data.get("comi_coo", 0))

    desc_consigna = nz_decimal(data.get("desc_consigna", 0))
    comision = nz_decimal(data.get("comision", 0))

    # ✅ Normalización correcta (36 / 0.36 / "36%")
    desc_proveedor_raw = getattr(producto, "descuento_proveedor", 0)
    desc_proveedor = normalize_percent(desc_proveedor_raw)

    # ✅ Excel: PPR = PVP - (PVP * DSCT_PROVE)
    precio_proveedor = q2(precio_be - (precio_be * desc_proveedor))

    out = {
        "producto_id": producto.id,
        "tipo_venta": tipo_venta,

        "precio_be": q2(precio_be),
        "desc_proveedor": q2(desc_proveedor),
        "precio_proveedor": q2(precio_proveedor),
    }

    # ==========================
    # PV / FERIA
    # ==========================
    if tipo_venta in ["PUNTO_DE_VENTA", "FERIA"]:

        # Tu UI hoy usa descuento_ie como %
        descuento_ie_monto = q2(precio_be * (descuento_ie / HUNDRED))
        precio_ie = q2(precio_be - descuento_ie_monto)

        # ganancia IE: PPFF - PIE (como tu backend actual)
        utilidad_ie = q2(precio_ppff - precio_ie)

        # precio coordinador: PIE - comisión coordinador
        precio_coo = q2(precio_ie - comi_coo)

        # utilidad BE x unidad: PRE_COO - PPR
        utilidad_be_x_un = q2(precio_coo - precio_proveedor)

        roi_percent = Decimal("0")
        if precio_proveedor > 0:
            roi_percent = q2((utilidad_be_x_un / precio_proveedor) * HUNDRED)

        out.update({
            "descuento_ie": q2(descuento_ie),
            "descuento_ie_monto": descuento_ie_monto,
            "precio_ie": precio_ie,

            "precio_ppff": q2(precio_ppff),
            "comi_coo": q2(comi_coo),
            "precio_coordinado": precio_coo,

            "utilidad_ie": utilidad_ie,
            "utilidad_be_x_un": utilidad_be_x_un,

            # compatibilidad con tu modelo actual
            "roi_ie": utilidad_be_x_un,
            "roi_percent": clamp_non_negative(roi_percent),
        })
        return out

    # ==========================
    # CONSIGNA
    # ==========================
    if tipo_venta == "CONSIGNA":
        # Precio consigna: BE - (BE * desc_consigna%)
        precio_consigna = q2(precio_be - (precio_be * (desc_consigna / HUNDRED)))
        precio_coordinado = q2(precio_consigna - comision)
        utilidad_be_x_un = q2(precio_coordinado - precio_proveedor)

        roi_percent = Decimal("0")
        if precio_proveedor > 0:
            roi_percent = q2((utilidad_be_x_un / precio_proveedor) * HUNDRED)

        out.update({
            "desc_consigna": q2(desc_consigna),
            "precio_consigna": precio_consigna,
            "comision": q2(comision),
            "precio_coordinado": precio_coordinado,
            "utilidad_be_x_un": utilidad_be_x_un,
            "roi_percent": clamp_non_negative(roi_percent),
        })
        return out

    raise ValueError("tipo_venta inválido")
