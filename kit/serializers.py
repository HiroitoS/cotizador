from decimal import Decimal
from rest_framework import serializers

from .models import Kit, KitItem

DEC_0 = Decimal("0.00")


class KitItemWriteSerializer(serializers.ModelSerializer):
    class Meta:
        model = KitItem
        fields = ["id", "producto", "cantidad", "orden"]


class KitWriteSerializer(serializers.ModelSerializer):
    items = KitItemWriteSerializer(many=True)

    class Meta:
        model = Kit
        fields = ["id", "nombre", "codigo_barra", "tipo", "activo", "observacion", "items"]

    def validate(self, attrs):
        items = attrs.get("items") or []
        if not items:
            raise serializers.ValidationError("Debes enviar al menos 1 item.")
        for it in items:
            if int(it.get("cantidad") or 0) <= 0:
                raise serializers.ValidationError("La cantidad debe ser mayor a 0.")
        return attrs

    def create(self, validated_data):
        items_data = validated_data.pop("items", [])
        kit = Kit.objects.create(**validated_data)
        KitItem.objects.bulk_create([KitItem(kit=kit, **it) for it in items_data])
        return kit

    def update(self, instance, validated_data):
        items_data = validated_data.pop("items", None)

        for k, v in validated_data.items():
            setattr(instance, k, v)
        instance.save()

        if items_data is not None:
            instance.items.all().delete()
            KitItem.objects.bulk_create([KitItem(kit=instance, **it) for it in items_data])

        return instance


class KitItemReadSerializer(serializers.ModelSerializer):
    producto_nombre = serializers.CharField(source="producto.nombre", read_only=True)
    producto_codigo = serializers.CharField(source="producto.codigo", read_only=True)
    editorial_nombre = serializers.CharField(source="producto.editorial.nombre", read_only=True)
    pvp_unitario = serializers.DecimalField(source="producto.pvp_2026", max_digits=12, decimal_places=2, read_only=True)
    pvp_subtotal = serializers.SerializerMethodField()

    class Meta:
        model = KitItem
        fields = [
            "id",
            "producto",
            "producto_codigo",
            "producto_nombre",
            "editorial_nombre",
            "cantidad",
            "orden",
            "pvp_unitario",
            "pvp_subtotal",
        ]

    def get_pvp_subtotal(self, obj):
        try:
            return obj.pvp_subtotal
        except Exception:
            return DEC_0


class KitReadSerializer(serializers.ModelSerializer):
    items = KitItemReadSerializer(many=True, read_only=True)
    total_items = serializers.IntegerField(read_only=True)
    pvp_total = serializers.DecimalField(max_digits=14, decimal_places=2, read_only=True)

    class Meta:
        model = Kit
        fields = [
            "id",
            "nombre",
            "codigo_barra",
            "tipo",
            "activo",
            "observacion",
            "created_at",
            "total_items",
            "pvp_total",
            "items",
        ]
