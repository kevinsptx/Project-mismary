from django.db import models
from django.contrib.auth.models import User


class Deuda(models.Model):
    cliente = models.CharField(max_length=100)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    saldo = models.DecimalField(max_digits=10, decimal_places=2)

    def __str__(self):
        return f"{self.cliente} - Saldo: ${self.saldo}"


class Abono(models.Model):
    deuda = models.ForeignKey(
        Deuda,
        on_delete=models.CASCADE,
        related_name='abonos'
    )

    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    vendedor = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True
    )

    def __str__(self):
        return f"Abono de ${self.valor}"
