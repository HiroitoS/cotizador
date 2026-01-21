from decimal import Decimal
from django.db import transaction
from django.db.models import Q
from django.http import HttpResponse
from rest_framework.views import APIView
from rest_framework.response import Response
from rest_framework.pagination import PageNumberPagination

from .models import (
    Editorial,
    Producto,
    Cotizacion,
    DetalleCotizacion,
    Adopcion,
    DetalleAdopcion,
    Pedido,
    DetallePedido,
    EstadoCotizacion,
    EstadoPedido,
    InstitucionEducativa,
    AsesorComercial,
)

from .serializers import (
    ProductoSerializer,
    CotizacionSerializer,
    CotizacionListSerializer,
    AdopcionSerializer,
    PedidoSerializer,
    InstitucionEducativaSerializer,
    AsesorComercialSerializer,
)

from .pricing import calcular_item
from .services_pdf import generar_pdf_cotizacion, generar_pdf_adopcion


# =========================================================
# PAGINACION
# =========================================================
class StandardPagination(PageNumberPagination):
    page_size = 30
    page_size_query_param = "page_size"
    max_page_size = 200


# =========================================================
# PRODUCTOS (V1)
# =========================================================
class ListarProductosView(APIView):
    def get(self, request):
        qs = Producto.objects.select_related("editorial").filter(estado=True).order_by("id")

        search = request.query_params.get("search")
        editorial = request.query_params.get("editorial")
        nivel = request.query_params.get("nivel")
        area = request.query_params.get("area")
        grado = request.query_params.get("grado")

        if search:
            qs = qs.filter(
                Q(nombre__icontains=search)
                | Q(codigo__icontains=search)
                | Q(editorial__nombre__icontains=search)
            )

        if editorial:
            # Front recomendado manda ID; mantenemos compatibilidad con nombre
            try:
                eid = int(editorial)
                qs = qs.filter(editorial_id=eid)
            except Exception:
                qs = qs.filter(editorial__nombre__iexact=editorial)

        if nivel:
            qs = qs.filter(nivel__iexact=nivel)

        if area:
            qs = qs.filter(area__iexact=area)

        if grado:
            qs = qs.filter(grado__iexact=grado)

        paginator = StandardPagination()
        page = paginator.paginate_queryset(qs, request)
        serializer = ProductoSerializer(page, many=True)
        return paginator.get_paginated_response(serializer.data)


class FiltrosProductosView(APIView):
    def get(self, request):
        qs = Producto.objects.select_related("editorial").filter(estado=True)

        editoriales = list(
            Editorial.objects.filter(productos__estado=True)
            .distinct()
            .order_by("nombre")
            .values("id", "nombre")
        )

        niveles = list(qs.values_list("nivel", flat=True).distinct().exclude(nivel="").order_by("nivel"))
        areas = list(qs.values_list("area", flat=True).distinct().exclude(area="").order_by("area"))
        grados = list(qs.values_list("grado", flat=True).distinct().exclude(grado="").order_by("grado"))

        return Response(
            {
                "editoriales": editoriales,
                "niveles": niveles,
                "areas": areas,
                "grados": grados,
            }
        )


# =========================================================
# CALCULO (V1)
# =========================================================
class CalcularDetalleView(APIView):
    def post(self, request):
        try:
            producto_id = request.data.get("producto_id")
            tipo_venta = request.data.get("tipo_venta")

            if not producto_id:
                return Response({"detail": "producto_id es requerido"}, status=400)

            producto = Producto.objects.select_related("editorial").get(id=producto_id)
            out = calcular_item(tipo_venta, producto, request.data)
            return Response(out, status=200)

        except Producto.DoesNotExist:
            return Response({"detail": "Producto no existe"}, status=404)
        except Exception as e:
            return Response({"detail": f"Error en cálculo: {str(e)}"}, status=400)


class CalcularBatchView(APIView):
    def post(self, request):
        try:
            tipo_venta = request.data.get("tipo_venta")
            items = request.data.get("items", [])

            if not tipo_venta:
                return Response({"detail": "tipo_venta es requerido"}, status=400)

            if not isinstance(items, list) or not items:
                return Response({"detail": "items debe ser una lista no vacía"}, status=400)

            productos_ids = [x.get("producto_id") for x in items if x.get("producto_id")]
            productos = {
                p.id: p
                for p in Producto.objects.filter(id__in=productos_ids).select_related("editorial")
            }

            out_items = []
            for x in items:
                pid = x.get("producto_id")
                if not pid or pid not in productos:
                    continue
                out_items.append(calcular_item(tipo_venta, productos[pid], x))

            return Response({"tipo_venta": tipo_venta, "items": out_items}, status=200)

        except Exception as e:
            return Response({"detail": f"Error batch: {str(e)}"}, status=400)


# =========================================================
# COTIZACIONES (V1)
# =========================================================
class GuardarCotizacionView(APIView):
    @transaction.atomic
    def post(self, request):
        try:
            institucion_id = request.data.get("institucion_id")
            asesor_id = request.data.get("asesor_id")
            tipo_venta = request.data.get("tipo_venta")
            items = request.data.get("items", [])

            if not institucion_id:
                return Response({"detail": "institucion_id es requerido"}, status=400)
            if not tipo_venta:
                return Response({"detail": "tipo_venta es requerido"}, status=400)
            if not items:
                return Response({"detail": "Debe enviar items"}, status=400)

            cot = Cotizacion.objects.create(
                institucion_id=institucion_id,
                asesor_id=asesor_id or None,
            )

            productos_ids = [x.get("producto_id") for x in items if x.get("producto_id")]
            productos = {
                p.id: p
                for p in Producto.objects.filter(id__in=productos_ids).select_related("editorial")
            }

            for x in items:
                pid = x.get("producto_id")
                if not pid or pid not in productos:
                    continue

                calc = calcular_item(tipo_venta, productos[pid], x)

                descuento_ie = Decimal(calc.get("descuento_ie", 0) or 0)
                precio_ie = Decimal(calc.get("precio_ie", calc.get("precio_consigna", 0)) or 0)
                precio_ppff = Decimal(calc.get("precio_ppff", 0) or 0)
                utilidad_ie = Decimal(calc.get("utilidad_ie", 0) or 0)

                DetalleCotizacion.objects.create(
                    cotizacion=cot,
                    producto_id=pid,
                    cantidad=int(x.get("cantidad") or 1),
                    precio_be=Decimal(calc.get("precio_be") or 0),
                    desc_proveedor=Decimal(calc.get("desc_proveedor") or 0),
                    precio_proveedor=Decimal(calc.get("precio_proveedor") or 0),
                    descuento_ie=descuento_ie,
                    precio_ie=precio_ie,
                    precio_ppff=precio_ppff,
                    utilidad_ie=utilidad_ie,
                    roi_ie=Decimal(calc.get("utilidad_be_x_un") or 0),
                    tipo_venta=calc.get("tipo_venta"),
                )

            return Response(CotizacionSerializer(cot).data, status=201)

        except Exception as e:
            return Response({"detail": f"Error guardando: {str(e)}"}, status=400)


class ListarCotizacionesView(APIView):
    def get(self, request):
        qs = Cotizacion.objects.select_related("institucion", "asesor").prefetch_related("detalles").order_by("-id")
        return Response(CotizacionListSerializer(qs, many=True).data, status=200)


class DetalleCotizacionRetrieveView(APIView):
    def get(self, request, pk):
        try:
            cot = (
                Cotizacion.objects.select_related("institucion", "asesor")
                .prefetch_related("detalles__producto__editorial")
                .get(pk=pk)
            )
            return Response(CotizacionSerializer(cot).data, status=200)
        except Cotizacion.DoesNotExist:
            return Response({"detail": "Cotización no existe"}, status=404)


class CambiarEstadoCotizacionView(APIView):
    def patch(self, request, pk):
        try:
            cot = Cotizacion.objects.get(pk=pk)
            estado = request.data.get("estado")
            motivo = request.data.get("motivo", "")

            if estado not in EstadoCotizacion.values:
                return Response({"detail": "Estado inválido"}, status=400)

            cot.estado = estado
            update_fields = ["estado"]

            if estado == EstadoCotizacion.RECHAZADA and hasattr(cot, "motivo_rechazo"):
                cot.motivo_rechazo = motivo
                update_fields.append("motivo_rechazo")

            cot.save(update_fields=update_fields)
            return Response({"detail": "Estado actualizado"}, status=200)

        except Cotizacion.DoesNotExist:
            return Response({"detail": "Cotización no existe"}, status=404)


class PDFCotizacionView(APIView):
    def get(self, request, pk):
        try:
            cot = (
                Cotizacion.objects.select_related("institucion", "asesor")
                .prefetch_related("detalles__producto__editorial")
                .get(pk=pk)
            )
            pdf_bytes = generar_pdf_cotizacion(cot)
            resp = HttpResponse(pdf_bytes, content_type="application/pdf")
            resp["Content-Disposition"] = f'attachment; filename="Cotizacion_{cot.numero_cotizacion or cot.id}.pdf"'
            return resp
        except Cotizacion.DoesNotExist:
            return Response({"detail": "Cotización no existe"}, status=404)
        except Exception as e:
            return Response({"detail": f"Error PDF: {str(e)}"}, status=400)


# =========================================================
# ADOPCIONES (V1)
# =========================================================
class CrearAdopcionView(APIView):
    @transaction.atomic
    def post(self, request):
        try:
            cotizacion_id = request.data.get("cotizacion_id")
            items = request.data.get("items", [])

            if not cotizacion_id:
                return Response({"detail": "cotizacion_id es requerido"}, status=400)

            cot = Cotizacion.objects.select_for_update().get(id=cotizacion_id)

            if cot.estado not in [EstadoCotizacion.APROBADA, EstadoCotizacion.PENDIENTE]:
                return Response({"detail": "La cotización no se puede adoptar en este estado."}, status=400)

            adopcion, _ = Adopcion.objects.get_or_create(cotizacion=cot)

            adopcion.detalles.all().delete()

            total = 0
            for x in items:
                detalle_id = x.get("detalle_id")
                cantidad = int(x.get("cantidad") or 0)
                mes_lectura = x.get("mes_lectura") or None

                if cantidad <= 0:
                    continue

                det = DetalleCotizacion.objects.select_related("producto").get(id=detalle_id, cotizacion=cot)

                DetalleAdopcion.objects.create(
                    adopcion=adopcion,
                    producto=det.producto,
                    cantidad_adoptada=cantidad,
                    mes_lectura=mes_lectura,
                )
                total += cantidad

            adopcion.cantidad_total = total
            adopcion.save(update_fields=["cantidad_total"])

            cot.estado = EstadoCotizacion.ADOPTADA
            cot.save(update_fields=["estado"])

            return Response({"detail": "Adopción registrada correctamente."}, status=201)

        except Cotizacion.DoesNotExist:
            return Response({"detail": "Cotización no existe"}, status=404)
        except DetalleCotizacion.DoesNotExist:
            return Response({"detail": "Detalle no existe"}, status=404)
        except Exception as e:
            return Response({"detail": f"Error adopción: {str(e)}"}, status=400)


class ListarAdopcionesView(APIView):
    def get(self, request):
        qs = (
            Adopcion.objects.select_related("cotizacion__institucion", "cotizacion__asesor")
            .prefetch_related("detalles__producto__editorial", "cotizacion__detalles")
            .order_by("-id")
        )
        return Response(AdopcionSerializer(qs, many=True).data, status=200)


class ExportarAdopcionPDFView(APIView):
    def get(self, request, adopcion_id):
        try:
            adop = (
                Adopcion.objects.select_related("cotizacion__institucion", "cotizacion__asesor")
                .prefetch_related("detalles__producto__editorial", "cotizacion__detalles")
                .get(id=adopcion_id)
            )
            pdf_bytes = generar_pdf_adopcion(adop)
            resp = HttpResponse(pdf_bytes, content_type="application/pdf")
            resp["Content-Disposition"] = f'attachment; filename="Adopcion_{adop.cotizacion.numero_cotizacion or adop.id}.pdf"'
            return resp
        except Adopcion.DoesNotExist:
            return Response({"detail": "Adopción no existe"}, status=404)
        except Exception as e:
            return Response({"detail": f"Error PDF: {str(e)}"}, status=400)


# =========================================================
# PEDIDOS (V1)
# =========================================================
class ListarPedidosView(APIView):
    def get(self, request):
        qs = (
            Pedido.objects.select_related("adopcion__cotizacion")
            .prefetch_related("detalles__producto__editorial")
            .order_by("-id")
        )
        return Response(PedidoSerializer(qs, many=True).data, status=200)


class CrearPedidoView(APIView):
    @transaction.atomic
    def post(self, request):
        try:
            adopcion_id = request.data.get("adopcion_id")
            if not adopcion_id:
                return Response({"detail": "adopcion_id es requerido"}, status=400)

            adop = (
                Adopcion.objects.select_related("cotizacion")
                .prefetch_related("detalles__producto")
                .get(id=adopcion_id)
            )

            pedido, _ = Pedido.objects.get_or_create(adopcion=adop)

            pedido.detalles.all().delete()
            for det in adop.detalles.all():
                DetallePedido.objects.create(
                    pedido=pedido,
                    producto=det.producto,
                    cantidad=det.cantidad_adoptada,
                    precio_proveedor=det.producto.precio_proveedor,
                )

            pedido.estado = EstadoPedido.BORRADOR
            pedido.save(update_fields=["estado"])

            return Response({"detail": "Pedido creado"}, status=201)

        except Adopcion.DoesNotExist:
            return Response({"detail": "Adopción no existe"}, status=404)
        except Exception as e:
            return Response({"detail": f"Error pedido: {str(e)}"}, status=400)


# =========================================================
# MAESTROS (V1)
# =========================================================
class ListarAsesoresView(APIView):
    def get(self, request):
        qs = AsesorComercial.objects.all().order_by("nombre")
        return Response(AsesorComercialSerializer(qs, many=True).data, status=200)


class ListarColegiosView(APIView):
    def get(self, request):
        qs = InstitucionEducativa.objects.all().order_by("nombre")
        return Response(InstitucionEducativaSerializer(qs, many=True).data, status=200)
