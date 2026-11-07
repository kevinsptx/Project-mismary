# MisMary

MisMary es una aplicación web que hicimos para manejar una tienda informal de venta por catálogo.
Sirve para llevar en un solo lugar los clientes, los productos, las ventas, lo que nos deben, lo que
compramos a los proveedores y la plata que entra y sale.

## Qué hace

* **Inicio:** un panel con lo vendido hoy, pedidos por recibir, productos sin stock, lo que nos deben y más.
* **Clientes:** registrarlos y ver su historial de ventas y abonos.
* **Productos:** categorías, precio de compra, precio de venta y stock.
* **Ventas:** registrar ventas con pago inicial, abonos y deudas. Al vender baja el stock.
* **Ventas pendientes y abonos:** controlar lo que cada cliente todavía debe.
* **Pedidos:** compras a proveedores. Al marcar un pedido como recibido, el stock sube y se crea el costo.
* **Proveedores:** registrarlos y consultar su información.
* **Reembolsos:** al reembolsar una venta se devuelve lo que el cliente pagó, se cierra su deuda
  y, si quieres, los productos vuelven al inventario. Queda guardado quién y cuándo.
* **Gastos hormiga:** registrar, editar y eliminar los gastos pequeños.
* **Reportes:** ingresos, costos, balance y clientes con deuda. Se pueden descargar en CSV.
* **Usuarios y grupos:** inicio de sesión con roles.

## Roles

| Rol | Qué puede hacer |
|---|---|
| Administrador | Todo: ver, registrar, editar y eliminar |
| Usuario | Solo ver y registrar |

El superusuario también puede crear usuarios y administrar los grupos.
La sesión se cierra sola después de 10 minutos sin usar la aplicación.

## Reglas importantes

* Un **pedido ya recibido** no se puede eliminar (su stock ya se sumó).
* Un **producto con ventas** no se puede eliminar, para no perder el historial.
* Al **eliminar una venta** se borran también sus pagos, su deuda, sus abonos y su reembolso.
* Al **reembolsar una venta**, su deuda queda cancelada y deja de aparecer en "Por cobrar".

## Tecnologías

* Python
* Django
* SQLite
* HTML y CSS

## Instalación

Clonar el repositorio y entrar a la carpeta:

```
git clone https://github.com/kevinsptx/Project-mismary.git
cd Project-mismary
```

Crear y activar un entorno virtual (recomendado):

```
python -m venv .venv
source .venv/bin/activate        # en Windows: .venv\Scripts\activate
```

Instalar dependencias:

```
pip install -r requirements.txt
```

Crear la base de datos:

```
python manage.py migrate
```

Crear el primer usuario administrador:

```
python manage.py createsuperuser
```

Ejecutar:

```
python manage.py runserver
```

Luego abrir http://127.0.0.1:8000 en el navegador.

## Datos de ejemplo

Para probar la aplicación con información de mentira hay unos comandos:

```
python manage.py cargar_datos --crear-usuarios    # carga datos de ejemplo y crea admin_demo y usuario_demo
python manage.py cargar_datos --limpiar           # borra lo del negocio y vuelve a cargar los datos
python manage.py limpiar_datos                    # solo borra los datos del negocio (antes hace una copia)
python manage.py arreglar_roles                   # deja bien los permisos de Administrador y Usuario
```

Los usuarios de ejemplo (`admin_demo` y `usuario_demo`) tienen la clave `demo1234`.
Los comandos de limpiar no borran usuarios ni grupos.

## Estructura

```
SGV_mismary/    clientes, productos, ventas, pedidos, reembolsos, gastos y reportes
accounts/       inicio de sesión, usuarios y grupos
core/           configuración del proyecto
```

## Proyecto

Este es un proyecto académico que estamos desarrollando para mejorar el manejo y control
de una pequeña tienda de venta por catálogo.