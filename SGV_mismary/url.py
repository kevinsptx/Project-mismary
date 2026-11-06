from django.urls import path
from . import views

urlpatterns = [

    # ----- INICIO -----
    path('', views.home, name='home'),

    # ----- CLIENTES -----
    path('register_cliente/', views.register_cliente, name='register_cliente'),
    path('list_cliente/', views.list_cliente, name='list_cliente'),
    path('details_cliente/<int:id>', views.cliente_details, name='details_cliente'),
    path('cliente_update/<int:id>', views.cliente_update, name='cliente_update'),
    path('cliente_delete/<int:id>', views.cliente_delete, name='cliente_delete'),
    path('cliente_historial/<int:id>', views.cliente_historial, name='cliente_historial'),

    # ----- PRODUCTOS -----
    path('register_producto/', views.register_producto, name='register_producto'),
    path('list_producto/', views.list_producto, name='list_producto'),
    path('productos/<int:id>/editar/', views.producto_update, name='producto_update'),
    path('productos/<int:id>/eliminar/', views.producto_delete, name='producto_delete'),
    path('productos_mas_vendidos/', views.productos_mas_vendidos, name='productos_mas_vendidos'),

    # ----- VENTAS -----
    path('register_venta/', views.register_venta, name='register_venta'),
    path('ventas/', views.list_venta, name='list_venta'),
    path('details_venta/<int:id>', views.venta_details, name='details_venta'),
    path('venta_delete/<int:id>', views.venta_delete, name='venta_delete'),
    path('ventas/<int:venta_id>/cancelar/', views.cancelar_venta, name='cancelar_venta'),
    path('consultar_por_fecha/', views.consultar_por_fecha, name='consultar_por_fecha'),

    # ----- VENTAS PENDIENTES (deudas de clientes) -----
    path('ventas/pendientes/', views.ventas_pendientes, name='ventas_pendientes'),
    path('ventas/pendientes/<int:deuda_id>/', views.detalle_pendiente, name='detalle_pendiente'),
    path('ventas/pendientes/<int:deuda_id>/pagar/', views.marcar_pagada, name='marcar_pagada'),
    path('ventas/pendientes/<int:deuda_id>/eliminar/', views.eliminar_pendiente, name='eliminar_pendiente'),
    path('deuda/<int:deuda_id>/', views.detalle_deuda, name='detalle_deuda'),

    # ----- ABONOS -----
    path('deuda/<int:deuda_id>/abono/', views.registrar_abono, name='registrar_abono'),
    path('abonos/', views.lista_abonos, name='lista_abonos'),
    path('abono/<int:abono_id>/editar/', views.editar_abono, name='editar_abono'),
    path('abono/<int:abono_id>/eliminar/', views.eliminar_abono, name='eliminar_abono'),

    # ----- REEMBOLSOS -----
    path('reembolsos/', views.lista_reembolsos, name='lista_reembolsos'),
    path('reembolsos/solicitar/<int:venta_id>/', views.solicitar_reembolso, name='solicitar_reembolso'),
    path('reembolsos/detalle/<int:reembolso_id>/', views.details_reembolso, name='details_reembolso'),
    path('reembolsos/venta/<int:venta_id>/', views.details_reembolso_venta, name='details_reembolso_venta'),
    path('reembolsos/registrar-devolucion/<int:reembolso_id>/', views.registrar_devolucion, name='registrar_devolucion'),

    # ----- PEDIDOS (compras a proveedores) -----
    path('pedidos/', views.list_pedido, name='list_pedido'),
    path('pedidos/registrar/', views.register_pedido, name='register_pedido'),
    path('pedidos/<int:pedido_id>/', views.pedido_details, name='pedido_details'),
    path('pedidos/<int:pedido_id>/eliminar/', views.eliminar_pedido, name='eliminar_pedido'),

    # ----- PROVEEDORES -----
    path('proveedores/', views.list_proveedor, name='list_proveedor'),
    path('proveedores/registrar/', views.register_proveedor, name='register_proveedor'),
    path('proveedores/<int:proveedor_id>/', views.proveedor_details, name='proveedor_details'),
    path('proveedores/<int:proveedor_id>/editar/', views.proveedor_update, name='proveedor_update'),
    path('proveedores/<int:proveedor_id>/eliminar/', views.proveedor_delete, name='proveedor_delete'),

    # ----- GASTOS HORMIGA (registrar, editar, eliminar) -----
    path('gastos/registrar/', views.registrar_gasto, name='registrar_gasto'),
    path('gastos/<int:gasto_id>/editar/', views.editar_gasto, name='editar_gasto'),
    path('gastos/<int:gasto_id>/eliminar/', views.eliminar_gasto, name='eliminar_gasto'),

    # ----- REPORTES - menú y descarga -----
    path('reportes/', views.reportes, name='reportes'),
    path('reportes/descargar/', views.descargar_reporte, name='descargar_reporte'),

    # ----- REPORTES - ingresos -----
    path('reportes/ingresos/', views.reporte_ingresos, name='reporte_ingresos'),
    path('reportes/ingresos/por-dia/', views.reporte_ingresos_dias, name='reporte_ingresos_dias'),
    path('reportes/ingresos/forma-pago/', views.reporte_ingresos_pagos, name='reporte_ingresos_pagos'),

    # ----- REPORTES - costos -----
    path('reportes/gastos/', views.reporte_gastos, name='reporte_gastos'),
    path('reportes/gastos/detalle/', views.reporte_gastos_detalle, name='reporte_gastos_detalle'),
    path('reportes/gastos/hormiga/', views.reporte_gastos_hormiga, name='reporte_gastos_hormiga'),
    path('reportes/gastos/por-recibir/', views.reporte_gastos_pendientes, name='reporte_gastos_pendientes'),

    # ----- REPORTES - balance y clientes con deuda -----
    path('reportes/balance/', views.reporte_balance, name='reporte_balance'),
    path('reportes/clientes_deuda/', views.reporte_clientes_deuda, name='reporte_clientes_deuda'),
]