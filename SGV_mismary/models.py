from django.db import models
from django.core.validators import MinValueValidator
from django.utils import timezone


class Cliente(models.Model):
    nombre = models.CharField(max_length=100)
    direccion = models.CharField(max_length=150, default='')
    telefono = models.CharField(max_length=10, default='')

    def __str__(self):
        return self.nombre


class Categoria(models.Model):
    nombre = models.CharField(max_length=100, unique=True)

    def __str__(self):
        return self.nombre


class Producto(models.Model):
    nombre = models.CharField(max_length=200)

    # Se actualiza automáticamente al registrar un pedido a proveedor.
    precio_compra = models.DecimalField(
        max_digits=10,
        decimal_places=2,
        default=0
    )

    precio_venta = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    cantidad_disponible = models.PositiveIntegerField(
        default=0
    )

    categoria = models.ForeignKey(
        Categoria,
        on_delete=models.PROTECT,
        related_name='productos'
    )

    def __str__(self):
        return self.nombre



class Venta(models.Model):

    ESTADOS = [
        ("Activa", "Activa"),
        ("Cancelada", "Cancelada"),
    ]

    cliente = models.ForeignKey(
        Cliente,
        on_delete=models.PROTECT,
        related_name='ventas'
    )

    valor_total = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    fecha = models.DateField()

    forma_pago = models.CharField(
        max_length=20,
        choices=[
            ('Efectivo', 'Efectivo'),
            ('Nequi', 'Nequi'),
            ('Daviplata', 'Daviplata'),
            ('Transferencia', 'Transferencia'),
        ],
        default='Efectivo',
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="Activa"
    )

    def __str__(self):
        return f"Venta de {self.cliente} - ${self.valor_total}"


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


class Pago(models.Model):
    venta = models.ForeignKey(
        Venta,
        on_delete=models.PROTECT,
        related_name='pagos'
    )

    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    fecha = models.DateTimeField(
        auto_now_add=True
    )

    def __str__(self):
        return f"Pago de ${self.valor} - {self.fecha.strftime('%d/%m/%Y')}"


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

    forma_pago = models.CharField(
        max_length=20,
        choices=[
            ('Efectivo', 'Efectivo'),
            ('Nequi', 'Nequi'),
            ('Daviplata', 'Daviplata'),
            ('Transferencia', 'Transferencia'),
        ],
        default='Efectivo',
    )

    def __str__(self):
        return (
            f"Abono ${self.valor} - "
            f"{self.fecha.strftime('%d/%m/%Y')}"
        )


class DetalleVenta(models.Model):
    venta = models.ForeignKey(
        Venta,
        on_delete=models.CASCADE,
        related_name='detalles'
    )

    producto = models.ForeignKey(
        Producto,
        on_delete=models.PROTECT,
        related_name='detalles_venta'
    )

    cantidad = models.PositiveIntegerField()

    precio = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    def __str__(self):
        return f'{self.producto.nombre} - {self.cantidad} unidades'


class Gasto(models.Model):
    TIPOS_GASTO = [
        ('Pedido', 'Pedido'),
        ('Hormiga', 'Hormiga'),
    ]

    descripcion = models.CharField(max_length=200)

    valor = models.DecimalField(
        max_digits=10,
        decimal_places=2
    )

    fecha = models.DateField()

    tipo = models.CharField(
        max_length=20,
        choices=TIPOS_GASTO,
        default='Hormiga'
    )

    def __str__(self):
        return f"{self.descripcion} - ${self.valor}"


# ===== PROVEEDORES =====

class Proveedor(models.Model):
    nombre = models.CharField(max_length=150, unique=True)
    telefono = models.CharField(max_length=20, blank=True)
    correo = models.EmailField(blank=True)
    direccion = models.CharField(max_length=200, blank=True)
    creado = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ['nombre']
        verbose_name_plural = 'proveedores'

    def __str__(self):
        return self.nombre


# ===== PEDIDOS =====

class Pedido(models.Model):
    ESTADOS = [
        ('Pendiente', 'Pendiente'),
        ('Recibido', 'Recibido'),
        ('Cancelado', 'Cancelado'),
    ]

    # Campo ANTIGUO (texto): guarda el nombre de los pedidos viejos.
    # Los pedidos nuevos usan el campo "proveedor" de abajo.
    proveedor_texto = models.CharField(max_length=150, blank=True)

    # Campo NUEVO: proveedor elegido de la lista
    proveedor = models.ForeignKey(
        Proveedor,
        on_delete=models.PROTECT,
        related_name='pedidos',
        null=True,
        blank=True,
    )

    fecha = models.DateField()
    estado = models.CharField(max_length=20, choices=ESTADOS, default='Pendiente')
    costo_total = models.DecimalField(max_digits=12, decimal_places=2, default=0)

    def __str__(self):
        return f"Pedido #{self.id} - {self.proveedor or self.proveedor_texto}"


class DetallePedido(models.Model):
    pedido = models.ForeignKey(Pedido, on_delete=models.CASCADE, related_name='detalles')
    producto = models.ForeignKey(Producto, on_delete=models.CASCADE)
    cantidad = models.PositiveIntegerField()
    costo_unitario = models.DecimalField(max_digits=12, decimal_places=2)

class Reembolso(models.Model):

    ESTADOS = [
        ("Solicitado", "Solicitado"),
        ("Pendiente", "Pendiente"),
        ("Devuelto", "Devuelto"),
        ("No aplica", "No aplica"),
    ]

    METODOS = [
        ("Efectivo", "Efectivo"),
        ("Transferencia", "Transferencia"),
        ("Otro", "Otro"),
    ]

    venta = models.OneToOneField(
        "SGV_mismary.Venta",
        on_delete=models.PROTECT,
        related_name="reembolso"
    )

    motivo = models.TextField(
        verbose_name="Motivo de la devolución"
    )

    monto = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        validators=[MinValueValidator(0)]
    )

    estado = models.CharField(
        max_length=20,
        choices=ESTADOS,
        default="Solicitado"
    )

    metodo = models.CharField(
        max_length=20,
        choices=METODOS,
        default="Efectivo"
    )

    fecha_solicitud = models.DateTimeField(
        default=timezone.now
    )

    fecha_devolucion = models.DateTimeField(
        null=True,
        blank=True
    )

    observaciones = models.TextField(
        blank=True
    )

    def __str__(self):
        return f"Reembolso de venta #{self.venta_id}"