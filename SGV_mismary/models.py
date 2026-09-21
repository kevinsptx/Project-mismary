from decimal import Decimal

from django.core.validators import MinValueValidator
from django.db import models
from django.utils import timezone


class Cliente(models.Model):
    nombre = models.CharField(max_length=150)

    def __str__(self):
        return self.nombre


class Venta(models.Model):
    """HU-010: venta por catálogo (cliente, valor total y fecha)."""

    cliente = models.ForeignKey(
        Cliente, on_delete=models.PROTECT, related_name="ventas"
    )
    valor_total = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(Decimal("0.01"))],
    )
    fecha = models.DateField(default=timezone.localdate)

    def __str__(self):
        return f"Venta #{self.pk} - {self.cliente} - {self.valor_total}"