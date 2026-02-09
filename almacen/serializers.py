from decimal import Decimal
from django.db.models import Sum, F, DecimalField, ExpressionWrapper
from rest_framework import serializers

from .models import (
    Almacen,
    Ingreso,
    IngresoDetalle,
    Transferencia,
    TransferenciaDetalle,
    Stock,
    MovimientoStock,
)

DEC_0 = Decimal("0.00")


# =========================================================
# ALMACEN
# =========================================================
class AlmacenSerializer(serializers.ModelSerializer):
    class Meta:
        model = Almacen
        fields = ["id", "nombre", "tipo", "es_principal", "activo", "created_at"]


# =========================================================
# INGRESO
# =========================================================
class IngresoDetalleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = IngresoDetalle
        fields = ["id", "producto", "cantidad", "costo_unitario"]


class IngresoWriteSerializer(serializers.ModelSerializer):
    detalles = IngresoDetalleWriteSerializer(many=True)

    class Meta:
        model = Ingreso
        fields = [
            "id",
            "almacen_destino",
            "proveedor",
            "tipo_documento",
            "numero_documento",
            "fecha_documento",
            "observacion",
            "detalles",
        ]

    def validate(self, attrs):
        detalles = attrs.get("detalles") or []
        if not detalles:
            raise serializers.ValidationError("Debe enviar al menos 1 detalle.")
        for d in detalles:
            if int(d.get("cantidad") or 0) <= 0:
                raise serializers.ValidationError("La cantidad debe ser mayor a 0.")
            if d.get("costo_unitario") is None:
                raise serializers.ValidationError("costo_unitario es requerido.")
        return attrs

    def create(self, validated_data):
        detalles_data = validated_data.pop("detalles", [])
        ingreso = Ingreso.objects.create(**validated_data)
        IngresoDetalle.objects.bulk_create(
            [IngresoDetalle(ingreso=ingreso, **d) for d in detalles_data]
        )
        return ingreso

    def update(self, instance, validated_data):
        detalles_data = validated_data.pop("detalles", None)

        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()

        if detalles_data is not None:
            instance.detalles.all().delete()
            IngresoDetalle.objects.bulk_create(
                [IngresoDetalle(ingreso=instance, **d) for d in detalles_data]
            )

        return instance


class IngresoDetalleReadSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    editorial_nombre = serializers.CharField(source="producto.editorial.nombre", read_only=True)
    subtotal = serializers.SerializerMethodField()

    class Meta:
        model = IngresoDetalle
        fields = [
            "id",
            "producto",
            "producto_nombre",
            "editorial_nombre",
            "cantidad",
            "costo_unitario",
            "subtotal",
        ]

    def get_subtotal(self, obj):
        try:
            return (obj.cantidad or 0) * (obj.costo_unitario or DEC_0)
        except Exception:
            return DEC_0


class IngresoReadSerializer(serializers.ModelSerializer):
    almacen_destino_nombre = serializers.CharField(source="almacen_destino.nombre", read_only=True)
    proveedor_nombre = serializers.CharField(source="proveedor.nombre", read_only=True)
    detalles = IngresoDetalleReadSerializer(many=True, read_only=True)

    total_cantidad = serializers.SerializerMethodField()
    total_valorizado = serializers.SerializerMethodField()

    class Meta:
        model = Ingreso
        fields = [
            "id",
            "almacen_destino",
            "almacen_destino_nombre",
            "proveedor",
            "proveedor_nombre",
            "tipo_documento",
            "numero_documento",
            "fecha_documento",
            "created_at",
            "observacion",
            "total_cantidad",
            "total_valorizado",
            "detalles",
        ]

    def get_total_cantidad(self, obj):
        return obj.detalles.aggregate(s=Sum("cantidad"))["s"] or 0

    def get_total_valorizado(self, obj):
        expr = ExpressionWrapper(
            F("cantidad") * F("costo_unitario"),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        )
        return obj.detalles.aggregate(s=Sum(expr))["s"] or DEC_0


# =========================================================
# TRANSFERENCIA
# =========================================================
class TransferenciaDetalleWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = TransferenciaDetalle
        fields = ["id", "producto", "cantidad"]


class TransferenciaWriteSerializer(serializers.ModelSerializer):
    detalles = TransferenciaDetalleWriteSerializer(many=True)

    class Meta:
        model = Transferencia
        fields = [
            "id",
            "almacen_origen",
            "almacen_destino",
            "tipo_documento",
            "numero_documento",
            "fecha_documento",
            "observacion",
            "estado",
            "detalles",
        ]

    def validate(self, attrs):
        if attrs.get("almacen_origen") == attrs.get("almacen_destino"):
            raise serializers.ValidationError("El almacén origen y destino deben ser distintos.")

        detalles = attrs.get("detalles") or []
        if not detalles:
            raise serializers.ValidationError("Debe enviar al menos 1 detalle.")
        for d in detalles:
            if int(d.get("cantidad") or 0) <= 0:
                raise serializers.ValidationError("La cantidad debe ser mayor a 0.")
        return attrs

    def create(self, validated_data):
        detalles_data = validated_data.pop("detalles", [])
        trans = Transferencia.objects.create(**validated_data)
        TransferenciaDetalle.objects.bulk_create(
            [TransferenciaDetalle(transferencia=trans, **d) for d in detalles_data]
        )
        return trans

    def update(self, instance, validated_data):
        detalles_data = validated_data.pop("detalles", None)

        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()

        if detalles_data is not None:
            instance.detalles.all().delete()
            TransferenciaDetalle.objects.bulk_create(
                [TransferenciaDetalle(transferencia=instance, **d) for d in detalles_data]
            )

        return instance


class TransferenciaDetalleReadSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    editorial_nombre = serializers.CharField(source="producto.editorial.nombre", read_only=True)

    class Meta:
        model = TransferenciaDetalle
        fields = ["id", "producto", "producto_nombre", "editorial_nombre", "cantidad"]


class TransferenciaReadSerializer(serializers.ModelSerializer):
    almacen_origen_nombre = serializers.CharField(source="almacen_origen.nombre", read_only=True)
    almacen_destino_nombre = serializers.CharField(source="almacen_destino.nombre", read_only=True)
    detalles = TransferenciaDetalleReadSerializer(many=True, read_only=True)

    class Meta:
        model = Transferencia
        fields = [
            "id",
            "almacen_origen",
            "almacen_origen_nombre",
            "almacen_destino",
            "almacen_destino_nombre",
            "tipo_documento",
            "numero_documento",
            "fecha_documento",
            "estado",
            "observacion",
            "created_at",
            "detalles",
        ]


# =========================================================
# STOCK / KARDEX
# =========================================================
class StockSerializer(serializers.ModelSerializer):
    almacen_nombre = serializers.CharField(source="almacen.nombre", read_only=True)
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    editorial_nombre = serializers.CharField(source="producto.editorial.nombre", read_only=True)
    costo_promedio = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Stock
        fields = [
            "id",
            "almacen",
            "almacen_nombre",
            "producto",
            "producto_nombre",
            "editorial_nombre",
            "cantidad_actual",
            "stock_minimo",
            "punto_reposicion",
            "valorizado_actual",
            "costo_promedio",
            "updated_at",
        ]


class MovimientoStockSerializer(serializers.ModelSerializer):
    almacen_nombre = serializers.CharField(source="almacen.nombre", read_only=True)
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    editorial_nombre = serializers.CharField(source="producto.editorial.nombre", read_only=True)

    class Meta:
        model = MovimientoStock
        fields = [
            "id",
            "almacen",
            "almacen_nombre",
            "producto",
            "producto_nombre",
            "editorial_nombre",
            "tipo",
            "fecha",
            "tipo_documento",
            "numero_documento",
            "entrada",
            "salida",
            "costo_unitario",
            "costo_total",
        ]


# =========================================================
# AJUSTE STOCK (endpoint simple)
# =========================================================
class AjusteStockItemSerializer(serializers.Serializer):
    producto_id = serializers.IntegerField()
    tipo = serializers.ChoiceField(choices=["POS", "NEG"])
    cantidad = serializers.IntegerField(min_value=1)
    costo_unitario = serializers.DecimalField(
        max_digits=12, decimal_places=2, required=False, allow_null=True
    )


class AjusteStockSerializer(serializers.Serializer):
    almacen_id = serializers.IntegerField()
    motivo = serializers.CharField()
    tipo_documento = serializers.CharField(required=False, default="OTRO")
    numero_documento = serializers.CharField(required=False, allow_blank=True, default="")
    items = AjusteStockItemSerializer(many=True)

    def validate(self, attrs):
        items = attrs.get("items") or []
        if not items:
            raise serializers.ValidationError("Debe enviar al menos 1 item.")
        return attrs


# =========================================================
# STOCK ALERTAS + CONFIG
# =========================================================
class StockAlertaSerializer(serializers.ModelSerializer):
    almacen_nombre = serializers.CharField(source="almacen.nombre", read_only=True)
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    editorial_nombre = serializers.CharField(source="producto.editorial.nombre", read_only=True)
    nivel_alerta = serializers.SerializerMethodField()

    class Meta:
        model = Stock
        fields = [
            "id",
            "almacen",
            "almacen_nombre",
            "producto",
            "producto_nombre",
            "editorial_nombre",
            "cantidad_actual",
            "stock_minimo",
            "punto_reposicion",
            "valorizado_actual",
            "nivel_alerta",
            "updated_at",
        ]

    def get_nivel_alerta(self, obj):
        cant = int(obj.cantidad_actual or 0)
        minimo = int(obj.stock_minimo or 0)
        repos = int(obj.punto_reposicion or 0)

        if minimo > 0 and cant <= minimo:
            return "CRITICO"
        if repos > 0 and cant <= repos:
            return "ATENCION"
        return "OK"


class StockConfigSerializer(serializers.ModelSerializer):
    class Meta:
        model = Stock
        fields = ["id", "almacen", "producto", "stock_minimo", "punto_reposicion"]
