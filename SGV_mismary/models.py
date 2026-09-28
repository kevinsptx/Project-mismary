from django.db import models

class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    telefono = models.CharField(max_length=10)
    direccion = models.CharField(max_length=150)

    def __str__(self):
        return self.nombre


class Deuda(models.Model):

    ESTADOS = [
        ("Pendiente", "Pendiente"),
        ("Pagada", "Pagada"),
    ]

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.CASCADE,
        related_name="deudas"
    )

    valor_total = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    saldo = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="Pendiente"
    )

    def __str__(self):

        return (
            f"{self.cliente.nombre} - "
            f"Saldo: ${self.saldo} - "
            f"{self.estado}"
        )


class Abono(models.Model):

    deuda = models.ForeignKey(
        Deuda,
        on_delete=models.CASCADE,
        related_name="abonos"
    )

    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):

        return f"Abono ${self.valor}"
class Venta(models.Model):
    cliente = models.ForeignKey(Cliente, on_delete=models.CASCADE)
    valor_total = models.DecimalField(max_digits=10, decimal_places=2)
    fecha = models.DateField()

    def __str__(self):
        return f"Venta de {self.cliente} - ${self.valor_total}"
